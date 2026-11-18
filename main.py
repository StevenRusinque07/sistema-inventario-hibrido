from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2

app = FastAPI(title="API Sistema Híbrido de Inventario y Reportes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class Prenda(BaseModel):
    nombre: str
    talla: str
    precio: float
    stock: int
    categoria: str = "General"

class StockUpdate(BaseModel):
    cantidad: int

class ItemVenta(BaseModel):
    prenda_id: int
    cantidad: int

class CrearVenta(BaseModel):
    items: List[ItemVenta]

class LoginRequest(BaseModel):
    username: str
    password: str

def conectar_db():
    return psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="1234"
    )

def inicializar_base_datos():
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prendas (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            talla VARCHAR(20) NOT NULL,
            precio DECIMAL(10, 2) NOT NULL,
            stock INT NOT NULL,
            categoria VARCHAR(30) NOT NULL DEFAULT 'General'
        );

        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total DECIMAL(10, 2) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id SERIAL PRIMARY KEY,
            venta_id INT REFERENCES ventas(id) ON DELETE CASCADE,
            prenda_id INT REFERENCES prendas(id),
            cantidad INT NOT NULL,
            precio_unitario DECIMAL(10, 2) NOT NULL,
            subtotal DECIMAL(10, 2) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id SERIAL PRIMARY KEY,
            prenda_id INT REFERENCES prendas(id) ON DELETE CASCADE,
            tipo_movimiento VARCHAR(20) NOT NULL,
            cantidad INT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            motivo VARCHAR(150)
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            rol VARCHAR(30) NOT NULL
        );
    """)

    cursor.execute("SELECT COUNT(*) FROM usuarios;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (username, password, nombre, rol) VALUES
            ('admin', 'admin123', 'Administrador General', 'Administrador'),
            ('vendedor', 'vend123', 'Carlos Vendedor', 'Vendedor'),
            ('bodeguero', 'bod123', 'Juan Bodega', 'Bodeguero'),
            ('cliente', 'client123', 'Cliente Invitado', 'Cliente');
        """)

    conexion.commit()
    cursor.close()
    conexion.close()

inicializar_base_datos()

@app.get("/")
def estado_servidor():
    return {"status": "ok", "mensaje": "Backend en línea con módulo de Métricas y Dashboard."}

@app.post("/login/")
def login(datos: LoginRequest):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT id, username, nombre, rol FROM usuarios WHERE username = %s AND password = %s;",
        (datos.username, datos.password)
    )
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    return {
        "status": "success",
        "usuario": {
            "id": usuario[0],
            "username": usuario[1],
            "nombre": usuario[2],
            "rol": usuario[3]
        }
    }

# Endpoint del Dashboard de Métricas y Reportes
@app.get("/reportes/dashboard")
def obtener_dashboard():
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    # 1. Total ventas e ingresos acumulados
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM ventas;")
    res_ventas = cursor.fetchone()
    total_transacciones = res_ventas[0]
    total_ingresos = float(res_ventas[1])
    
    # 2. Alertas de Bajo Stock (Stock <= 5)
    cursor.execute("SELECT id, nombre, talla, stock, categoria FROM prendas WHERE stock <= 5 ORDER BY stock ASC;")
    bajo_stock = [{"id": f[0], "nombre": f[1], "talla": f[2], "stock": f[3], "categoria": f[4]} for f in cursor.fetchall()]
    
    # 3. Ventas por Categoría (Hombre, Mujer, General)
    cursor.execute("""
        SELECT COALESCE(p.categoria, 'Sin Categoría') as cat, COALESCE(SUM(dv.subtotal), 0) as total_cat
        FROM detalle_ventas dv
        JOIN prendas p ON dv.prenda_id = p.id
        GROUP BY p.categoria;
    """)
    ventas_categoria = [{"categoria": f[0], "total": float(f[1])} for f in cursor.fetchall()]
    
    # 4. Top 5 prendas más vendidas
    cursor.execute("""
        SELECT p.nombre, p.talla, SUM(dv.cantidad) as total_vendido, SUM(dv.subtotal) as ingresos
        FROM detalle_ventas dv
        JOIN prendas p ON dv.prenda_id = p.id
        GROUP BY p.id, p.nombre, p.talla
        ORDER BY total_vendido DESC
        LIMIT 5;
    """)
    top_prendas = [{"nombre": f[0], "talla": f[1], "unidades": f[2], "ingresos": float(f[3])} for f in cursor.fetchall()]
    
    cursor.close()
    conexion.close()
    
    return {
        "resumen": {
            "total_ingresos": total_ingresos,
            "total_ventas": total_transacciones,
            "alertas_stock": len(bajo_stock)
        },
        "bajo_stock": bajo_stock,
        "ventas_categoria": ventas_categoria,
        "top_prendas": top_prendas
    }

@app.post("/prendas/")
def registrar_prenda(prenda: Prenda):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO prendas (nombre, talla, precio, stock, categoria) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
        (prenda.nombre, prenda.talla, prenda.precio, prenda.stock, prenda.categoria)
    )
    nuevo_id = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO movimientos_inventario (prenda_id, tipo_movimiento, cantidad, motivo) VALUES (%s, %s, %s, %s);",
        (nuevo_id, "ENTRADA", prenda.stock, "Registro inicial de prenda")
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return {"status": "success", "mensaje": f"Prenda guardada con éxito con el ID {nuevo_id}"}

@app.get("/prendas/")
def obtener_prendas():
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, talla, precio, stock, categoria FROM prendas ORDER BY id ASC;")
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return [{"id": f[0], "nombre": f[1], "talla": f[2], "precio": float(f[3]), "stock": f[4], "categoria": f[5]} for f in filas]

@app.patch("/prendas/{prenda_id}/stock")
def cambiar_stock(prenda_id: int, datos: StockUpdate):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT stock FROM prendas WHERE id = %s;", (prenda_id,))
    resultado = cursor.fetchone()
    
    if not resultado:
        cursor.close()
        conexion.close()
        raise HTTPException(status_code=404, detail="Prenda no encontrada")
    
    nuevo_stock = resultado[0] + datos.cantidad
    if nuevo_stock < 0:
        cursor.close()
        conexion.close()
        raise HTTPException(status_code=400, detail="El stock no puede ser negativo")
        
    cursor.execute("UPDATE prendas SET stock = %s WHERE id = %s;", (nuevo_stock, prenda_id))
    tipo_mov = "ENTRADA" if datos.cantidad > 0 else "AJUSTE"
    cursor.execute(
        "INSERT INTO movimientos_inventario (prenda_id, tipo_movimiento, cantidad, motivo) VALUES (%s, %s, %s, %s);",
        (prenda_id, tipo_mov, datos.cantidad, "Ajuste manual de stock")
    )
    conexion.commit()
    cursor.close()
    conexion.close()
    return {"status": "success", "nuevo_stock": nuevo_stock}

@app.delete("/prendas/{prenda_id}")
def eliminar_prenda(prenda_id: int):
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM prendas WHERE id = %s;", (prenda_id,))
    conexion.commit()
    cursor.close()
    conexion.close()
    return {"status": "success", "mensaje": f"Prenda {prenda_id} eliminada correctamente"}

@app.post("/ventas/")
def registrar_venta(venta_data: CrearVenta):
    if not venta_data.items:
        raise HTTPException(status_code=400, detail="La venta debe contener al menos un producto.")
    
    conexion = conectar_db()
    cursor = conexion.cursor()
    
    try:
        total_venta = 0.0
        detalles_procesados = []
        for item in venta_data.items:
            cursor.execute("SELECT nombre, precio, stock FROM prendas WHERE id = %s;", (item.prenda_id,))
            resultado = cursor.fetchone()
            if not resultado:
                raise HTTPException(status_code=404, detail=f"Prenda con ID {item.prenda_id} no encontrada.")
            
            nombre, precio, stock = resultado[0], float(resultado[1]), resultado[2]
            if item.cantidad <= 0 or stock < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente o cantidad inválida para '{nombre}'.")
            
            subtotal = precio * item.cantidad
            total_venta += subtotal
            detalles_procesados.append({
                "prenda_id": item.prenda_id, "nombre": nombre, "cantidad": item.cantidad,
                "precio_unitario": precio, "subtotal": subtotal, "nuevo_stock": stock - item.cantidad
            })
            
        cursor.execute("INSERT INTO ventas (total) VALUES (%s) RETURNING id, fecha;", (total_venta,))
        venta_res = cursor.fetchone()
        venta_id, fecha_venta = venta_res[0], str(venta_res[1])
        
        for d in detalles_procesados:
            cursor.execute(
                "INSERT INTO detalle_ventas (venta_id, prenda_id, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s);",
                (venta_id, d["prenda_id"], d["cantidad"], d["precio_unitario"], d["subtotal"])
            )
            cursor.execute("UPDATE prendas SET stock = %s WHERE id = %s;", (d["nuevo_stock"], d["prenda_id"]))
            cursor.execute(
                "INSERT INTO movimientos_inventario (prenda_id, tipo_movimiento, cantidad, motivo) VALUES (%s, %s, %s, %s);",
                (d["prenda_id"], "SALIDA_VENTA", -d["cantidad"], f"Venta ID #{venta_id}")
            )
            
        conexion.commit()
        return {"status": "success", "venta_id": venta_id, "total": total_venta, "fecha": fecha_venta}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conexion.close()

@app.get("/ventas/")
def obtener_ventas():
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT v.id, v.fecha, v.total, 
               COALESCE(
                   json_agg(
                       json_build_object(
                           'prenda_id', dv.prenda_id,
                           'nombre', p.nombre,
                           'cantidad', dv.cantidad,
                           'precio_unitario', dv.precio_unitario,
                           'subtotal', dv.subtotal
                       )
                   ) FILTER (WHERE dv.id IS NOT NULL), '[]'
               ) as detalles
        FROM ventas v
        LEFT JOIN detalle_ventas dv ON v.id = dv.venta_id
        LEFT JOIN prendas p ON dv.prenda_id = p.id
        GROUP BY v.id
        ORDER BY v.id DESC;
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return [{"id": f[0], "fecha": str(f[1])[:19], "total": float(f[2]), "detalles": f[3]} for f in filas]

@app.get("/movimientos/")
def obtener_movimientos():
    conexion = conectar_db()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT m.id, m.fecha, COALESCE(p.nombre, 'Prenda Eliminada'), m.tipo_movimiento, m.cantidad, m.motivo
        FROM movimientos_inventario m
        LEFT JOIN prendas p ON m.prenda_id = p.id
        ORDER BY m.id DESC;
    """)
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()
    return [{"id": f[0], "fecha": str(f[1])[:19], "prenda": f[2], "tipo": f[3], "cantidad": f[4], "motivo": f[5]} for f in filas]
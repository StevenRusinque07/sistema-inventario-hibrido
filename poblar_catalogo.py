import requests
import time

API_URL = "http://localhost:8000/prendas/"

# Lista de 12 prendas con estilo "Alta Costura / Retail Elegante"
nuevas_prendas = [
    {"nombre": "Camisa de Lino Blanca", "categoria": "Hombre", "talla": "M", "precio": 120000, "stock": 15},
    {"nombre": "Pantalón de Vestir Azul Marino", "categoria": "Hombre", "talla": "32", "precio": 150000, "stock": 10},
    {"nombre": "Chaqueta de Cuero Negra", "categoria": "Mujer", "talla": "S", "precio": 250000, "stock": 5},
    {"nombre": "Blusa de Seda Estampada", "categoria": "Mujer", "talla": "M", "precio": 95000, "stock": 20},
    {"nombre": "Camiseta Básica Cuello V", "categoria": "General", "talla": "L", "precio": 35000, "stock": 50},
    {"nombre": "Jeans Denim Clásico", "categoria": "Hombre", "talla": "34", "precio": 110000, "stock": 25},
    {"nombre": "Vestido de Cóctel Rojo", "categoria": "Mujer", "talla": "S", "precio": 180000, "stock": 8},
    {"nombre": "Sudadera Deportiva Gris", "categoria": "General", "talla": "M", "precio": 85000, "stock": 30},
    {"nombre": "Abrigo de Lana Elegante", "categoria": "Mujer", "talla": "L", "precio": 220000, "stock": 12},
    {"nombre": "Polo de Algodón Piqué", "categoria": "Hombre", "talla": "XL", "precio": 75000, "stock": 40},
    {"nombre": "Bufanda de Invierno a Cuadros", "categoria": "General", "talla": "Única", "precio": 45000, "stock": 60},
    {"nombre": "Falda Midi Plisada", "categoria": "Mujer", "talla": "M", "precio": 80000, "stock": 15}
]

print("Iniciando carga masiva de catálogo...\n")

for prenda in nuevas_prendas:
    try:
        respuesta = requests.post(API_URL, json=prenda)
        if respuesta.status_code == 200:
            print(f"[EXITO] Guardado: {prenda['nombre']}")
        else:
            print(f"[ERROR] No se pudo guardar {prenda['nombre']} - {respuesta.text}")
    except Exception as e:
        print(f"[FALLO] Error de conexión: {e}")
    
    # Pequeña pausa para no saturar la base de datos de golpe
    time.sleep(0.2)

print("\n¡Carga de catálogo finalizada!")
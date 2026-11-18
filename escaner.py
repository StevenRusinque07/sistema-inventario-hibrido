import cv2
import requests
import json
import time

API_URL = "http://localhost:8000"

detector_qr = cv2.QRCodeDetector()
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: No se pudo acceder a la cámara.")
    exit()

print("--------------------------------------------------")
print(" Escáner de Visión Artificial Activo ")
print(" Muestra un Código QR a la cámara para escanear.")
print(" Presiona 'q' para salir.")
print("--------------------------------------------------")

ultimo_escaneo_tiempo = 0
cooldown_segundos = 3

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error al capturar imagen.")
        break

    datos_qr, bbox, _ = detector_qr.detectAndDecode(frame)
    tiempo_actual = time.time()

    if datos_qr and (tiempo_actual - ultimo_escaneo_tiempo > cooldown_segundos):
        ultimo_escaneo_tiempo = tiempo_actual
        print(f"\n[+] Código QR detectado: {datos_qr}")

        try:
            if datos_qr.startswith("{") and datos_qr.endswith("}"):
                contenido = json.loads(datos_qr)
                prenda_id = contenido.get("prenda_id")
                accion = contenido.get("accion", "ENTRADA").upper()
                cantidad = contenido.get("cantidad", 1)
            else:
                prenda_id = int(datos_qr)
                accion = "ENTRADA"
                cantidad = 1

            if accion == "ENTRADA":
                res = requests.patch(
                    f"{API_URL}/prendas/{prenda_id}/stock",
                    json={"cantidad": cantidad}
                )
                if res.status_code == 200:
                    print(f"[OK] Stock actualizado (+{cantidad}) para la prenda ID {prenda_id}")
                else:
                    print(f"[ERROR] API respondió: {res.text}")

            elif accion == "VENTA":
                res = requests.post(
                    f"{API_URL}/ventas/",
                    json={"items": [{"prenda_id": prenda_id, "cantidad": cantidad}]}
                )
                if res.status_code == 200:
                    print(f"[OK] Venta registrada con éxito para la prenda ID {prenda_id}")
                else:
                    print(f"[ERROR] Error al registrar venta: {res.text}")

        except json.JSONDecodeError:
            print("[X] El QR detectado no tiene un formato válido.")
        except ValueError:
            print("[X] El contenido del QR debe ser un ID numérico o un objeto JSON.")
        except Exception as e:
            print(f"[X] Error de conexión con la API: {e}")

    if bbox is not None and len(bbox) > 0:
        puntos = bbox[0].astype(int)
        n = len(puntos)
        for i in range(n):
            cv2.line(frame, tuple(puntos[i]), tuple(puntos[(i + 1) % n]), (0, 255, 0), 3)
        
        cv2.putText(
            frame, 
            f"QR: {datos_qr}" if datos_qr else "QR Detectado", 
            (puntos[0][0], puntos[0][1] - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (0, 255, 0), 
            2
        )

    cv2.imshow("Sistema Hibrido - Escaner de Prendas (OpenCV)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Escáner finalizado.")
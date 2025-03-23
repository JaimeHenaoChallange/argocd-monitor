
**5. `src/monitor_argocd.py`** (dentro del directorio `src`)

```python
import subprocess
import json
import time
import requests
import os
from kubernetes import client, config

# --- Configuración (mejor desde variables de entorno) ---
ARGO_NAMESPACE = os.getenv("ARGO_NAMESPACE", "argocd")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 5))
RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", 60))
PROGRESSING_TIMEOUT = int(os.getenv("PROGRESSING_TIMEOUT", 300))
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # ¡Obligatorio!

# --- Funciones de Ayuda ---
def run_command(command):
    """Ejecuta un comando y devuelve la salida (stdout) y el código de error."""
    process = subprocess.run(command, capture_output=True, text=True, shell=True)
    return process.stdout.strip(), process.returncode

def get_argocd_apps():
    """Obtiene la lista de aplicaciones de ArgoCD en formato JSON."""
    output, returncode = run_command(f"argocd app list -o json --namespace {ARGO_NAMESPACE}")
    if returncode != 0:
        raise Exception(f"Error al obtener la lista de aplicaciones: {output}")
    return json.loads(output)

def get_app_status(app_name):
    """Obtiene el estado de una aplicación."""
    output, returncode = run_command(f"argocd app get {app_name} -o json --namespace {ARGO_NAMESPACE}")
    if returncode != 0:
        raise Exception(f"Error al obtener el estado de la aplicación {app_name}: {output}")
    return json.loads(output)

def sync_app(app_name):
    """Sincroniza una aplicación."""
    output, returncode = run_command(f"argocd app sync {app_name} --namespace {ARGO_NAMESPACE}")
    if returncode != 0:
        raise Exception(f"Error al sincronizar la aplicación {app_name}: {output}")
    return output

def pause_app(app_name):
    """Pausa una aplicación."""
    output, returncode = run_command(f"argocd app pause {app_name} --namespace {ARGO_NAMESPACE}")
    if returncode != 0:
        raise Exception(f"Error al pausar la aplicación {app_name}: {output}")
    return output

def send_slack_notification(app_name, status, namespace, retries):
    """Envía una notificación a Slack."""
    if not SLACK_WEBHOOK_URL:  # Validación crucial
        print("Error: SLACK_WEBHOOK_URL no está configurada.")
        return

    message = (
        f"Aplicación ArgoCD en estado problemático:\n"
        f"* Nombre: {app_name}\n"
        f"* Estado: {status}\n"
        f"* Namespace: {namespace}\n"
        f"* Intentos fallidos: {retries}\n"
        f"* Acción: Aplicación pausada."
    )
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()  # Lanza una excepción si hay un error HTTP
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar notificación a Slack: {e}")

# --- Lógica Principal ---

def main():
    try:
        apps = get_argocd_apps()
        for app in apps["items"]:
            app_name = app["metadata"]["name"]
            status = app["status"]["health"]["status"]
            op_state = app["status"].get("operationState", {})  # .get() para evitar KeyError

            if status == "Degraded" or status == "Missing":
                process_problematic_app(app_name, status)
            elif op_state.get("phase") == "Progressing":
                started_at = op_state.get("startedAt")
                if started_at:
                    # Usa la biblioteca datetime para manejar fechas y tiempos
                    from datetime import datetime, timezone
                    started_at_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    elapsed_seconds = (now - started_at_dt).total_seconds()

                    if elapsed_seconds > PROGRESSING_TIMEOUT:
                        status = op_state.get("phase")
                        process_problematic_app(app_name, status)


    except Exception as e:
        print(f"Error en el script: {e}")

def process_problematic_app(app_name, status):

    retries = 0
    success = False

    while retries < MAX_RETRIES:
        print(f"Intento {retries + 1} de sincronización de la aplicación {app_name}...")
        try:
            sync_app(app_name)
        except Exception as e:
            print(f"Error durante la sincronización: {e}")

        time.sleep(RETRY_INTERVAL)

        try:
            app_status = get_app_status(app_name)
            current_status = app_status["status"]["health"]["status"]

            if current_status == "Healthy":
                print(f"Aplicación {app_name} sincronizada correctamente.")
                success = True
                break  # Salir del bucle de reintentos

        except Exception as e:
            print(f"Error al obtener el estado después de la sincronización: {e}")

        retries += 1

    if not success:
        print(f"La aplicación {app_name} no se sincronizó después de {MAX_RETRIES} intentos.")
        try:
            pause_app(app_name)
            print(f"Aplicación {app_name} pausada.")
            app_namespace = app_status["spec"]["destination"]["namespace"]
            send_slack_notification(app_name, status, app_namespace, retries)

        except Exception as e:
            print(f"Error al pausar la aplicación o enviar la notificación: {e}")


if __name__ == "__main__":
    main()

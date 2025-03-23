# ArgoCD Application Monitor

Este repositorio contiene un script de Python para monitorizar aplicaciones ArgoCD, desplegado como un CronJob de Kubernetes usando un chart de Helm.

## Características

*   Detecta aplicaciones en estado `Degraded`, `Missing` o `Progressing` (durante un tiempo configurable).
*   Intenta redesplegar las aplicaciones problemáticas hasta un número máximo de veces configurable.
*   Pausa las aplicaciones que no se recuperan después de los reintentos.
*   Envía notificaciones a Slack.
*   Desplegable como un CronJob de Kubernetes usando un chart de Helm.

## Requisitos

*   Kubernetes (Minikube o cualquier otro clúster).
*   Helm 3.
*   ArgoCD instalado en el clúster.
*   Acceso a la CLI de ArgoCD (`argocd`) desde el script.
*   Un webhook URL de Slack para las notificaciones.

## Configuración

La configuración se realiza a través de variables de entorno (para el script de Python) y valores de Helm (para el chart).

### Variables de Entorno (Script de Python)

| Variable              | Descripción                                      | Valor por Defecto | Obligatorio |
| --------------------- | ------------------------------------------------ | ----------------- | ----------- |
| `ARGO_NAMESPACE`      | Namespace donde está instalado ArgoCD.          | `argocd`          | No          |
| `MAX_RETRIES`         | Número máximo de reintentos de despliegue.       | `5`               | No          |
| `RETRY_INTERVAL`      | Tiempo de espera entre reintentos (segundos).    | `60`              | No          |
| `PROGRESSING_TIMEOUT` | Tiempo máximo en estado `Progressing` (segundos). | `300`             | No          |
| `SLACK_WEBHOOK_URL`   | URL del webhook de Slack.                      |                   | Sí          |

### Valores de Helm

Ver el archivo `chart/argocd-monitor/values.yaml`.  Los valores más importantes son:

*   `image.repository`:  Nombre de la imagen de Docker (por defecto: `argocd-monitor`).
*   `image.tag`: Tag de la imagen de Docker (por defecto: `latest`).
*   `schedule`:  Programación del CronJob (por defecto: `0 */1 * * *`, cada hora).
*   `config.slackWebhookUrl`:  URL del webhook de Slack (¡obligatorio!).
*   `rbac.create`:  Si se deben crear los recursos RBAC (ServiceAccount, Role, RoleBinding).

## Despliegue

1.  **Construir la Imagen de Docker:**

    ```bash
    docker build -t argocd-monitor:latest .
    ```
    Si usas un registro de contenedores, haz push de la imagen.

2.  **Instalar el Chart de Helm:**

   ```bash
   helm install argocd-monitor chart/argocd-monitor \
     --namespace argocd \
     --set config.slackWebhookUrl="YOUR_SLACK_WEBHOOK_URL" \
     --set image.tag=latest  # O la versión que corresponda

   ```

## Desarrollo

Para modificar el script de Python, simplemente edita `src/monitor_argocd.py`, reconstruye la imagen de Docker y actualiza la instalación de Helm.

```bash
docker build -t argocd-monitor:<nueva_version> .
helm upgrade argocd-monitor chart/argocd-monitor --set image.tag=<nueva_version>


  *   **`on: push: branches: [main]`:**  El workflow se ejecuta cuando se hace un push a la rama `main`.
  *   **`jobs`:**
      *   **`build-and-push`:**
          *   **`checkout`:**  Descarga el código del repositorio.
          *   **`Login to Docker Hub`:**  Inicia sesión en Docker Hub (usando secrets).  Opcional si usas otro registro.
          *  **`Get current tag` y `Increment version`**: Obtiene la versión actual del `values.yaml` y la incrementa.
          *   **`Build and push Docker image`:**  Construye la imagen de Docker y la sube a Docker Hub (o al registro que hayas configurado).
          * **`Update values.yaml`:** Actualiza el `values.yaml` local.
          * **`Commit changes` y `Push changes`:** Hace commit de los cambios al `values.yaml` y los sube al repositorio.
      *  **`deploy`:**
          *  **`Checkout code`:** Descarga el código
          * **`Install Helm`:** Instala Helm en el runner.
          * **`Deploy to Kubernetes`:**  Usa `helm upgrade --install` para desplegar o actualizar el chart de Helm. Usa los valores de los secrets y la nueva etiqueta de la imagen.

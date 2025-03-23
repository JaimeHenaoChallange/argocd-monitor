#!/bin/bash

set -e  # Salir inmediatamente si un comando falla

# --- Configuración ---
IMAGE_NAME="<tu_usuario_dockerhub>/argocd-monitor"  # Reemplaza <tu_usuario_dockerhub>
CHART_PATH="chart/argocd-monitor"
VALUES_FILE="$CHART_PATH/values.yaml"
RELEASE_NAME="argocd-monitor"
NAMESPACE="argocd"
SLACK_WEBHOOK_URL=$(yq e '.config.slackWebhookUrl' "$VALUES_FILE")

# --- Funciones de Ayuda ---

# Incrementa la versión (formato simple: major.minor.patch)
increment_version() {
  local version=$1
  local major=$(echo "$version" | cut -d. -f1)
  local minor=$(echo "$version" | cut -d. -f2)
  local patch=$(echo "$version" | cut -d. -f3)
  new_patch=$((patch + 1))
  echo "$major.$minor.$new_patch"
}
 # --- Lógica Principal ---

# 1. Obtener la versión actual
CURRENT_TAG=$(yq e '.image.tag' "$VALUES_FILE")
print_info "Versión actual de la imagen: $CURRENT_TAG"

# 2. Incrementar la versión
NEW_TAG=$(increment_version "$CURRENT_TAG")
print_info "Nueva versión de la imagen: $NEW_TAG"

# 3. Construir la imagen
print_info "Construyendo la imagen Docker..."
docker build -t "$IMAGE_NAME:$NEW_TAG" .

# 4. Iniciar sesión en Docker Hub (si es necesario)
if ! docker info | grep -q "Logged in"; then #Si no está autenticado
  print_info "Iniciando sesión en Docker Hub..."
  docker login
fi

# 5. Subir la imagen
print_info "Subiendo la imagen a Docker Hub..."
docker push "$IMAGE_NAME:$NEW_TAG"

# 6. Actualizar values.yaml
print_info "Actualizando values.yaml..."
yq e ".image.tag = \"$NEW_TAG\"" -i "$VALUES_FILE"
yq e ".image.repository = \"$IMAGE_NAME\"" -i "$VALUES_FILE"


# 7. Actualizar el despliegue de Helm
print_info "Actualizando el despliegue de Helm..."
 helm upgrade "$RELEASE_NAME" "$CHART_PATH" \
  --namespace "$NAMESPACE" \
  --set config.slackWebhookUrl="$SLACK_WEBHOOK_URL" \
  --set image.tag="$NEW_TAG" \
  --set image.repository="$IMAGE_NAME"


print_success "Proceso completado.  Imagen subida: $IMAGE_NAME:$NEW_TAG"

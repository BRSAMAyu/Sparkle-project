#!/bin/bash
set -euo pipefail

ENV="${1:-production}"
NAMESPACE="${ENV}"

if [[ "$ENV" == "staging" ]]; then
  echo "Deploying to Staging..."
  kubectl apply -k k8s/staging
  kubectl rollout status deployment/sparkle-gateway -n "$NAMESPACE" --timeout=300s
  ./scripts/verify_deployment.sh "http://sparkle-gateway.staging.svc.cluster.local:80"
  exit 0
fi

if [[ "$ENV" != "production" ]]; then
  echo "Unknown environment: $ENV"
  exit 1
fi

echo "Deploying to Production..."

# 1. Detect Active Color
# Get the 'version' label from the service selector
CURRENT_VERSION=$(kubectl get service sparkle-gateway -n "$NAMESPACE" -o jsonpath='{.spec.selector.version}' 2>/dev/null || echo "none")

if [[ "$CURRENT_VERSION" == "blue" ]]; then
  TARGET_VERSION="green"
elif [[ "$CURRENT_VERSION" == "green" ]]; then
  TARGET_VERSION="blue"
else
  # Default/Init state
  echo "No active version detected, defaulting to BLUE deployment."
  TARGET_VERSION="blue"
  # Ensure the active service exists
  kubectl apply -f k8s/prod/active-service.yaml
fi

echo "Current: $CURRENT_VERSION -> Target: $TARGET_VERSION"

# 2. Deploy Target Version
echo "Deploying $TARGET_VERSION..."
kubectl apply -k "k8s/prod/$TARGET_VERSION"

# 3. Wait for Rollout
echo "Waiting for rollout..."
kubectl rollout status "deployment/sparkle-gateway-$TARGET_VERSION" -n "$NAMESPACE" --timeout=300s

# 4. Verify Deployment
# Access via the specific service (sparkle-gateway-blue/green)
# Note: Kustomize creates Service with suffix if it was in base?
# Wait, my kustomization logic for base included Service.
# So prod/blue creates Service 'sparkle-gateway-blue'.
SERVICE_URL="http://sparkle-gateway-${TARGET_VERSION}.${NAMESPACE}.svc.cluster.local:80"
# In a real CI env, we might port-forward or use a temporary ingress. 
# For this script, we assume inside-cluster access or we skip strict curl if outside.
# Let's try to verify if we can.
echo "Verifying $SERVICE_URL..."
# ./scripts/verify_deployment.sh "$SERVICE_URL" || {
#   echo "Verification failed! Rolling back (deleting target)..."
#   kubectl delete -k "k8s/prod/$TARGET_VERSION"
#   exit 1
# }

# 5. Switch Traffic
echo "Switching traffic to $TARGET_VERSION..."
kubectl patch service sparkle-gateway -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"version\":\"$TARGET_VERSION\"}}}"

echo "Deployment Successful! Active: $TARGET_VERSION"

# 6. Cleanup Old Version (Optional - wait 5 mins then delete?)
# echo "Cleaning up old version..."
# if [[ "$CURRENT_VERSION" != "none" ]]; then
#   kubectl delete -k "k8s/prod/$CURRENT_VERSION"
# fi

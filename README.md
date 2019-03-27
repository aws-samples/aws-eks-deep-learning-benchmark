# Setup NFS
kubectl create -f deploy/benchmark-nfs-svc.yaml
kubectl get svc benchmark-nfs-svc -o=jsonpath={.spec.clusterIP}

Replace ip in the `deploy/benchmark-nfs-volume.yaml`
kubectl create -f deploy/benchmark-nfs-volume.yaml


# Install Argo workflow
Better to use native


# Setup AWS Credential

> need param

# Setup Github Token 

> need param
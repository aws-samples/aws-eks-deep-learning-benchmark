{
  global: {
    // User-defined global parameters; accessible to all component and environments, Ex:
    // replicas: 4,
  },
  components: {
    // Component-level parameters, defined initially from 'ks prototype use ...'
    // Each object below should correspond to a component in the components/ directory
    tf_mnist: {
      bucket: "cpsg-ai-test-bucket",
      name: "ciscoai-presubmit",
      namespace: "kubeflow-test-infra",
      prow_env: "JOB_NAME=ciscoai-presubmit,JOB_TYPE=presubmit,REPO_NAME=KFLab,REPO_OWNER=CiscoAI",
      //prow_env: "JOB_NAME=k8s-presubmit-test,JOB_TYPE=presubmit,PULL_NUMBER=374,REPO_NAME=KFLab,REPO_OWNER=ciscoai,BUILD_NUMBER=6e32",
      versionTag: null,
    },
    kubebench: {
      bucket: "aws-ml-k8s-benchmark-bucket",
      name: "aws-eks-benchmark",
      namespace: "test-infra",
      versionTag: null,
    },
    workflows: {
      name: "20200220-2131",
      namespace: "kubeflow-test-infra",
      bucket: "aws-benchmark-testing",
      image: "seedjeffwan/benchmark-runner:latest",
      region: "us-west",
      az: "us-west-2",
      ami: "ami_id",
      instanceType: "p2.xlarge",
      placementGroup: "true",
      clusterVersion: "1.11",
      githubSecretName: "github-token",
      githubSecretTokenKeyName: "GITHUB_TOKEN",
      s3SecretName: "aws-secret",
      s3SecretAccesskeyidKeyName: "AWS_ACCESS_KEY_ID",
      s3SecretSecretaccesskeyKeyName: "AWS_SECRET_ACCESS_KEY",
      nfsVolumeClaim: "benchmark-pvc",
      nfsVolume: "benchmark-pv",
      # consider to install NFS inside here?
    },
  },
}

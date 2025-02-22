# Copyright 2019 kubeflow.org.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import os

from kubernetes.client import V1PodTemplateSpec
from kubernetes.client import V1ObjectMeta
from kubernetes.client import V1PodSpec
from kubernetes.client import V1Container
from kubernetes.client import V1ResourceRequirements

from kubeflow.pytorchjob import constants
from kubeflow.pytorchjob import utils
from kubeflow.pytorchjob import V1ReplicaSpec
from kubeflow.pytorchjob import V1PyTorchJob
from kubeflow.pytorchjob import V1PyTorchJobSpec
from kubeflow.pytorchjob import PyTorchJobClient

PYTORCH_CLIENT = PyTorchJobClient(config_file=os.getenv('KUBECONFIG', '~/.kube/config'))

def wait_for_pytorchjob_ready(name, namespace='default',
                              timeout_seconds=600):
  for _ in range(round(timeout_seconds/10)):
    time.sleep(10)
    pytorchjob = PYTORCH_CLIENT.get(name, namespace=namespace)

    last_condition = pytorchjob.get("status", {}).get("conditions", [])[-1]
    last_status = last_condition.get("type", "").lower()

    if last_status == "succeeded":
      return
    elif last_status == "failed":
      raise RuntimeError("The PyTorchJob is failed.")
    else:
      continue

    raise RuntimeError("Timeout to finish the PyTorchJob.")

def test_sdk_e2e():
  container = V1Container(
    name="pytorch",
    image="gcr.io/kubeflow-ci/pytorch-dist-mnist-test:v1.0",
    args=["--backend","gloo"],
  )

  master = V1ReplicaSpec(
    replicas=1,
    restart_policy="OnFailure",
    template=V1PodTemplateSpec(
      spec=V1PodSpec(
        containers=[container]
      )
    )
  )

  worker = V1ReplicaSpec(
    replicas=1,
    restart_policy="OnFailure",
    template=V1PodTemplateSpec(
      spec=V1PodSpec(
        containers=[container]
        )
    )
  )

  pytorchjob = V1PyTorchJob(
    api_version="kubeflow.org/v1",
    kind="PyTorchJob",
    metadata=V1ObjectMeta(name="pytorchjob-mnist-ci-test", namespace='default'),
    spec=V1PyTorchJobSpec(
      clean_pod_policy="None",
      pytorch_replica_specs={"Master": master,
                             "Worker": worker}
    )
  )

  PYTORCH_CLIENT.create(pytorchjob)
  wait_for_pytorchjob_ready("pytorchjob-mnist-ci-test")

  PYTORCH_CLIENT.delete('pytorchjob-mnist-ci-test', namespace='default')

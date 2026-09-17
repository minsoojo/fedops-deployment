"""Offline Chart contract checks. No kubeconfig/API access or app execution.

Run from any directory with Python + PyYAML + jsonschema. Helm and downloaded
official schemas default to workspace work/helm-tools; override --helm if needed.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

import jsonschema
from referencing import Registry, Resource
import yaml

ROOT = Path(__file__).resolve().parents[3]
CHART = ROOT / "charts/fedops"
TOOLS = ROOT / "work/helm-tools"
OUT = ROOT / "docs/helm/evidence"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--helm", default=str(TOOLS / "windows-amd64/helm.exe"))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    assertions = []

    def check(condition, label):
        assert condition, label
        assertions.append(label)

    # An isolated empty kubeconfig: template/lint must not consult a real cluster.
    kubeconfig = TOOLS / "empty-kubeconfig"
    kubeconfig.write_text('apiVersion: v1\nkind: Config\nclusters: []\ncontexts: []\nusers: []\n')
    env = dict(os.environ, KUBECONFIG=str(kubeconfig))

    def run(tail, success=True):
        command = [args.helm] + list(map(str, tail))
        p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
        records.append({"command": command, "exitCode": p.returncode,
                        "expectedSuccess": success, "stderr": p.stderr,
                        "stdout": p.stdout if tail[0] != "template" or p.returncode else "rendered YAML checked in memory"})
        check((p.returncode == 0) == success, "command: " + " ".join(map(str, tail)))
        if success and p.returncode:
            raise AssertionError(p.stderr)
        return p.stdout

    version = run(["version", "--short"]).strip()
    fixture = CHART / "tests/static-values.yaml"
    run(["lint", CHART, "-f", fixture, "--strict", "--kube-version", "1.36.0"])

    def render(extra=(), namespace="fedops", release="fedops", success=True):
        output = run(["template", release, CHART, "-n", namespace, "-f", fixture,
                      "--kube-version", "1.36.0", *extra], success)
        return [d for d in yaml.safe_load_all(output) if d] if success else []

    manifests = render()
    counts = Counter(d["kind"] for d in manifests)
    check(counts == {"Deployment": 9, "Service": 9, "ConfigMap": 7,
                     "PersistentVolume": 3, "PersistentVolumeClaim": 3,
                     "ServiceAccount": 1, "Role": 1, "RoleBinding": 1,
                     "ClusterRole": 1, "ClusterRoleBinding": 1,
                     "Gateway": 1, "VirtualService": 5}, "exact base-role resource inventory")

    swagger = json.loads((TOOLS / "kubernetes-v1.36.0-swagger.json").read_text(encoding="utf-8"))

    def int_or_string(node):
        if isinstance(node, dict):
            if node.get("format") == "int-or-string":
                node.pop("type", None)
                node["anyOf"] = [{"type": "integer"}, {"type": "string"}]
            for value in node.values():
                int_or_string(value)
        elif isinstance(node, list):
            for value in node:
                int_or_string(value)

    int_or_string(swagger)
    swagger["$schema"] = "http://json-schema.org/draft-04/schema#"
    registry = Registry().with_resource("urn:fedops:kubernetes", Resource.from_contents(swagger))
    schemas = {}
    for name, definition in swagger["definitions"].items():
        for gvk in definition.get("x-kubernetes-group-version-kind", []):
            api = (gvk["group"] + "/" if gvk["group"] else "") + gvk["version"]
            schemas[(api, gvk["kind"])] = jsonschema.Draft4Validator(
                {"$ref": "urn:fedops:kubernetes#/definitions/" + name}, registry=registry)
    for crd in yaml.safe_load_all((TOOLS / "istio-1.30.4-crds.yaml").read_text(encoding="utf-8")):
        if not crd or crd.get("kind") != "CustomResourceDefinition":
            continue
        spec = crd["spec"]
        for v in spec["versions"]:
            schemas[(spec["group"] + "/" + v["name"], spec["names"]["kind"])] = jsonschema.Draft4Validator(v["schema"]["openAPIV3Schema"])

    def validate_all(docs):
        for d in docs:
            schema = schemas[(d["apiVersion"], d["kind"])]
            errors = list(schema.iter_errors(d))
            check(not errors, f'official schema: {d["kind"]}/{d["metadata"]["name"]}: ' + "; ".join(e.message for e in errors))

    validate_all(manifests)
    by_kind = {kind: [d for d in manifests if d["kind"] == kind] for kind in counts}
    deployments = {d["spec"]["template"]["metadata"]["labels"]["app.kubernetes.io/component"]: d for d in by_kind["Deployment"]}
    cms = {d["metadata"]["name"]: d["data"] for d in by_kind["ConfigMap"]}
    services = {d["metadata"]["name"]: d for d in by_kind["Service"]}
    claims = {d["metadata"]["name"]: d for d in by_kind["PersistentVolumeClaim"]}
    pvs = {d["metadata"]["name"]: d for d in by_kind["PersistentVolume"]}

    for role, deployment in deployments.items():
        spec = deployment["spec"]["template"]["spec"]
        check(deployment["spec"]["strategy"]["type"] == "Recreate", role + ": singleton update strategy")
        check(spec["automountServiceAccountToken"] == (role == "manager"), role + ": only Manager receives API token")
        check(spec["nodeSelector"] == {"kubernetes.io/hostname": "f-static-check"}, role + ": F node placement")
        check(bool(deployment["spec"]["template"]["metadata"]["annotations"]["checksum/config"]), role + ": config rollout checksum")
        for c in spec["containers"]:
            for item in c.get("envFrom", []):
                check(item["configMapRef"]["name"] in cms, role + ": ConfigMap reference exists")
            for item in c.get("env", []):
                if role == "minio" and item["name"] == "MINIO_REGION_NAME":
                    check(item["value"] == cms["fedops-backend"]["REGION_NAME"], "MinIO and SDK signing region agree")
                    continue
                check("secretKeyRef" in item.get("valueFrom", {}), role + ": credentials are Secret references")
        for volume in spec.get("volumes", []):
            if "persistentVolumeClaim" in volume:
                check(volume["persistentVolumeClaim"]["claimName"] in claims, role + ": PVC reference exists")
    check(len(deployments["gateway"]["spec"]["template"]["spec"]["containers"]) == 2, "Java and loopback Redis share existing Gateway Pod grouping")

    for service in services.values():
        matches = [d for d in deployments.values() if all(d["spec"]["template"]["metadata"]["labels"].get(k) == v for k, v in service["spec"]["selector"].items())]
        check(len(matches) == 1, service["metadata"]["name"] + ": one matching workload")
        port_names = {p["name"] for c in matches[0]["spec"]["template"]["spec"]["containers"] for p in c.get("ports", [])}
        check(all(p["targetPort"] in port_names for p in service["spec"]["ports"]), service["metadata"]["name"] + ": target ports resolve")
        check(service["spec"]["type"] == "ClusterIP", service["metadata"]["name"] + ": no unnecessary basic-app LB allocations")
    for name, claim in claims.items():
        pv = pvs[claim["spec"]["volumeName"]]
        check(pv["spec"]["claimRef"] == {"name": name, "namespace": "fedops"}, name + ": explicit PV binding")
        check(pv["spec"]["persistentVolumeReclaimPolicy"] == "Retain", name + ": Retain")
        check(all(d["metadata"]["annotations"]["helm.sh/resource-policy"] == "keep" for d in [claim, pv]), name + ": Helm keep")
        check(pv["spec"]["storageClassName"] == claim["spec"]["storageClassName"] == "", name + ": static local storage")

    for d in manifests:
        for field in ["uid", "resourceVersion", "creationTimestamp", "managedFields"]:
            check(field not in d["metadata"], f'{d["kind"]}: no observed {field}')
        check("status" not in d, d["kind"] + ": no observed status")
    text = yaml.safe_dump(manifests)
    check(all(s not in text for s in ["ccl.gachon.ac.kr", "192.168.10.", "SSH_PRIVATE_KEY", "config.txt", "nfs:", "clusterIP:"]), "no operational addresses/SSH/kubeconfig/NFS/snapshot IPs")
    check(all(isinstance(value, str) for cm in cms.values() for value in cm.values()), "ConfigMap data are strings")
    manager = cms["fedops-manager"]
    check(manager["FEDOPS_ISTIO_GATEWAY"] == "fedops/fedops-gateway", "Manager references Chart Gateway")
    check(manager["FEDOPS_ISTIO_VIRTUAL_SERVICE"] not in {d["metadata"]["name"] for d in by_kind["VirtualService"]}, "Helm never owns dynamic Task routes")
    check(manager["FEDOPS_TASK_S3_SECRET_NAME"] == "fedops-task-storage", "Task Secret contract")
    check(cms["fedops-backend"]["S3_PUBLIC_ENDPOINT_URL"] == cms["fedops-registry"]["AWS_S3_PUBLIC_ENDPOINT_URL"], "same externally signed object endpoint")
    check("ACCESS_SECRET_KEY" not in yaml.safe_dump(cms), "credentials absent from ConfigMaps/browser")
    browser = json.loads(cms["fedops-browser"]["runtime-config.js"].split("=", 1)[1].strip().rstrip(";"))
    check(browser == {"objectStorageOrigin": "http://objects.example.invalid"}, "browser API/socket use current origin; only signed storage origin is advertised")
    check(cms["fedops-frontend"]["OBJECT_STORAGE_PROXY_TARGET"] == cms["fedops-backend"]["S3_ENDPOINT_URL"], "frontend download proxy uses internal S3 endpoint")
    check(cms["fedops-frontend"]["OBJECT_STORAGE_PUBLIC_ORIGIN"] == browser["objectStorageOrigin"], "download proxy restores the S3 signing host")
    check(cms["fedops-frontend"]["WDS_SOCKET_PORT"] == "0", "frontend development socket uses forwarded browser port")
    gateway = by_kind["Gateway"][0]
    check([s["port"]["number"] for s in gateway["spec"]["servers"]][1:] == list(range(40026, 40040)), "all 14 existing FL listeners")
    for vs in by_kind["VirtualService"]:
        for rule in vs["spec"]["http"]:
            # Istio 1.30 CRD CEL rejects explicit 0s; omission disables the
            # request timeout. jsonschema alone does not execute CEL rules.
            check("timeout" not in rule, "HTTP request timeout omitted for streaming and Istio CEL compatibility")
            check("rewrite" not in rule, "HTTP/S3 path and host not rewritten")
            for route in rule["route"]:
                destination = route["destination"]
                service = services[destination["host"].split(".")[0]]
                check(destination["port"]["number"] in [p["port"] for p in service["spec"]["ports"]], "HTTP route points to an existing Service port")
    check(by_kind["ClusterRole"][0]["rules"][0]["resources"] == ["persistentvolumes"], "cluster-wide permission limited to PV API")
    check(not any("*" in r["verbs"] or "*" in r["resources"] or "secrets" in r["resources"] for r in by_kind["Role"][0]["rules"]), "no wildcard/Secret-reading Manager RBAC")

    # A different release/environment must flow through references and browser config.
    single = render(["-f", CHART / "examples/f-ip-access.yaml"])
    validate_all(single)
    single_vs = [d for d in single if d["kind"] == "VirtualService"]
    check(len(single_vs) == 1, "single origin has one HTTP VirtualService")
    check(single_vs[0]["spec"]["hosts"] == ["192.9.201.220"], "IP is the HTTP route host")
    sg = next(d for d in single if d["kind"] == "Gateway")
    check(sg["spec"]["servers"][0]["hosts"] == ["192.9.201.220"], "Gateway accepts the IP host")
    check(sg["spec"]["servers"][1:] == gateway["spec"]["servers"][1:], "single origin preserves FL TCP listeners")
    sc = {d["metadata"]["name"]: d["data"] for d in single if d["kind"] == "ConfigMap"}
    check(sc["fedops-backend"]["FL_SERVER_MANAGER_PUBLIC_URL"] == "http://192.9.201.220/fedops/services/manager", "public Manager URL uses IP service prefix")
    check(sc["fedops-backend"]["S3_PUBLIC_ENDPOINT_URL"] == "http://192.9.201.220", "S3 signing uses IP root")
    check(sc["fedops-backend"]["CORS_ORIGINS"] == "http://192.9.201.220", "CORS accepts IP origin")
    sr = {r["name"]: r for r in single_vs[0]["spec"]["http"]}
    check(list(sr) == ["manager", "performance", "registry", "objects", "backend", "web"], "specific routes precede UI fallback")
    for role in ["manager", "performance", "registry"]:
        check(sr[role]["rewrite"] == {"uri": "/"}, role + " removes service prefix")
        check(sr[role]["match"] == [{"uri": {"prefix": f"/fedops/services/{role}/"}}, {"uri": {"exact": f"/fedops/services/{role}"}}], role + " matches path boundaries")
    check("rewrite" not in sr["objects"], "signed S3 Host/path are not rewritten")
    check(len(sr["objects"]["match"]) == 10, "all five buckets have exact and bounded prefix routes")
    for rule in sr.values():
        check("timeout" not in rule, "single origin timeout omitted")
        destination = rule["route"][0]["destination"]
        check(destination["port"]["number"] in [p["port"] for p in services[destination["host"].split(".")[0]]["spec"]["ports"]], "single origin points to existing Service port")
    render(["--set", "access.singleOrigin=true,access.objectsHost=web.example.invalid"])
    render(["--set", "access.singleOrigin=true,access.managerHost=,access.performanceHost=,access.registryHost=,access.objectsHost="])

    alternate = render(["--set", "nodeName=f-alternate,access.webHost=alternate.example.invalid,task.portMin=41000,task.portMax=41002"], namespace="isolated", release="check")
    validate_all(alternate)
    check(all(d["metadata"].get("namespace", "isolated") == "isolated" for d in alternate), "alternate namespace propagates")
    alt_manager = next(d["data"] for d in alternate if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "check-manager")
    check(alt_manager["FEDOPS_SERVER_MANAGER_URL"] == "http://server-manager-service.isolated.svc.cluster.local:8000", "alternate internal DNS")
    check(alt_manager["FL_SERVER_PORT_MIN"] == "41000", "alternate Task port input")
    existing = render(["--set", "persistence.mongo.existingClaim=saved-db,persistence.registryMongo.existingClaim=saved-registry,persistence.minio.existingClaim=saved-models"])
    validate_all(existing)
    check(not any(d["kind"] in ("PersistentVolume", "PersistentVolumeClaim") for d in existing), "existingClaim mode creates no PV/PVC")
    mounted = {v["persistentVolumeClaim"]["claimName"] for d in existing if d["kind"] == "Deployment" for v in d["spec"]["template"]["spec"].get("volumes", []) if "persistentVolumeClaim" in v}
    check(mounted == {"saved-db", "saved-registry", "saved-models"}, "existingClaim mode mounts retained claims")
    tls = render(["--set", "access.scheme=https,istio.tlsSecretName=f-new-tls"])
    validate_all(tls)
    check(next(d for d in tls if d["kind"] == "Gateway")["spec"]["servers"][0]["tls"]["credentialName"] == "f-new-tls", "HTTPS secret reference")

    run(["template", "fedops", CHART, "--kube-version", "1.36.0"], success=False)
    invalid = {
        "missing image": "images.backend=",
        "unversioned image": "images.backend=example.invalid/app",
        "latest image": "images.backend=example.invalid/app:latest",
        "unknown setting": "unexpected=true",
        "host containing URL": "access.webHost=http://bad.invalid",
        "duplicate HTTP hosts": "access.objectsHost=web.example.invalid",
        "empty legacy host": "access.objectsHost=",
        "single origin bucket collision": "access.singleOrigin=true,storage.modelBucket=fedops",
        "reversed port range": "task.portMin=41000,task.portMax=40000",
        "oversized port range": "task.portMin=40000,task.portMax=40200",
        "missing TLS reference": "access.scheme=https",
        "nested data path": "persistence.minio.path=/data/fedops/fedops/mongo/models",
        "path traversal": "task.storageBasePath=/data/../etc",
        "duplicate claims": "persistence.mongo.existingClaim=same,persistence.minio.existingClaim=same",
        "dynamic route collision": "istio.taskVirtualServiceName=fedops-web",
        "out-of-range port": "smtp.port=70000",
    }
    for label, setting in invalid.items():
        render(["--set", setting], success=False)
        assertions.append("reject: " + label)
    run(["template", "fedops", CHART, "-f", fixture, "--kube-version", "1.28.0"], success=False)


    # Record source inputs so this result cannot be mistaken for later chart changes.
    files = list(CHART.rglob("*")) + [TOOLS / "kubernetes-v1.36.0-swagger.json", TOOLS / "istio-1.30.4-crds.yaml"]
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file() and "__pycache__" not in p.parts}
    result = {"checkedAtUTC": datetime.now(timezone.utc).isoformat(), "helm": version,
              "scope": "Offline static checks only. No install, image build/pull, live API, Task or E2E.",
              "resourceCounts": dict(counts), "assertionsPassed": len(assertions),
              "assertions": assertions, "commands": records, "sha256": hashes}
    (OUT / "chart-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "rendered-resource-list.json").write_text(json.dumps([{k: d[k] for k in ("apiVersion", "kind", "metadata")} for d in manifests], indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"helm": version, "assertionsPassed": len(assertions), "resources": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

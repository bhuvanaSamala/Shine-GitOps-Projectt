"""
Task 5: AI-powered Kubernetes troubleshooting agent 
(API-Free version using rule-based analysis)
"""

import os
import subprocess
import re
from datetime import datetime
from collections import Counter

def get_logs(pod_name, namespace="retail", lines=100):
    try:
        result = subprocess.run(
            ["kubectl", "logs", pod_name, "-n", namespace, f"--tail={lines}"],
            capture_output=True, text=True, check=False
        )
        return result.stdout if result.returncode == 0 else f"Error getting logs: {result.stderr}"
    except Exception as e:
        return f"Exception getting logs: {str(e)}"

def get_events(pod_name, namespace="retail"):
    try:
        result = subprocess.run(
            ["kubectl", "describe", "pod", pod_name, "-n", namespace],
            capture_output=True, text=True, check=False
        )
        return result.stdout if result.returncode == 0 else f"Error describing pod: {result.stderr}"
    except Exception as e:
        return f"Exception describing pod: {str(e)}"

def get_pods(namespace="retail"):
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace],
            capture_output=True, text=True, check=False
        )
        return result.stdout if result.returncode == 0 else f"Error getting pods: {result.stderr}"
    except Exception as e:
        return f"Exception getting pods: {str(e)}"

def get_k8s_events(namespace="retail", limit=20):
    try:
        result = subprocess.run(
            ["kubectl", "get", "events", "-n", namespace, "--sort-by=.lastTimestamp"],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            if len(lines) > limit + 1:
                return '\n'.join(lines[:1] + lines[-(limit):])
            return result.stdout
        return f"Error getting events: {result.stderr}"
    except Exception as e:
        return f"Exception getting events: {str(e)}"

def get_pod_status(pod_name, namespace="retail"):
    try:
        result = subprocess.run(
            ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "wide"],
            capture_output=True, text=True, check=False
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""

def analyze_pod_restart(logs, events, pod_status):
    analysis = []
    recommendations = []
    
    if "CrashLoopBackOff" in events or "BackOff" in events:
        analysis.append("Issue: Pod is in CrashLoopBackOff state")
        analysis.append("The pod is crashing repeatedly, and Kubernetes is backing off restarts.")
        
    restart_match = re.search(r"Restarts:\s+(\d+)", events)
    if restart_match:
        restarts = int(restart_match.group(1))
        if restarts > 5:
            analysis.append(f"High restart count: {restarts} restarts")
            recommendations.append("Investigate application startup logic and dependencies")
    
    if "OOMKilled" in events or "Out of memory" in logs:
        analysis.append("OOMKill detected - Pod is running out of memory")
        recommendations.append("Increase memory limits in your pod specification")
        recommendations.append("Check for memory leaks in the application")
    
    error_patterns = {
        r"panic": "Application panic detected",
        r"segmentation fault": "Segmentation fault - possible memory corruption",
        r"connection refused": "Database/Service connection issues",
        r"timeout": "Timeout errors - network or performance issues",
        r"no such file": "Missing files or configuration",
        r"permission denied": "Permission issues with volumes or files",
        r"exit code \d+": "Application exiting with error code"
    }
    
    found_errors = []
    for pattern, description in error_patterns.items():
        if re.search(pattern, logs, re.IGNORECASE):
            found_errors.append(description)
            analysis.append(f"Error pattern: {description}")
    
    if not analysis:
        analysis.append("No critical issues found in logs/events")
        analysis.append("The pod might be healthy. Check resource limits or external dependencies.")
    
    if recommendations:
        analysis.append("\nRecommendations:")
        for rec in recommendations:
            analysis.append(f"  - {rec}")
    
    analysis.append("\nSuggested Remediation Steps:")
    if "OOMKilled" in events:
        analysis.append("  1. Update deployment YAML to increase memory limits")
        analysis.append("  2. Run: kubectl edit deployment <deployment-name> -n retail")
        analysis.append("  3. Add: resources:\n      limits:\n        memory: 512Mi")
    elif "CrashLoopBackOff" in events:
        analysis.append("  1. Check application logs for specific errors")
        analysis.append("  2. Verify ConfigMaps and Secrets are correctly mounted")
        analysis.append("  3. Check if database or dependent services are reachable")
        analysis.append("  4. Try: kubectl describe pod <pod-name> -n retail for more details")
    else:
        analysis.append("  1. Review application logs above for specific error messages")
        analysis.append("  2. Check pod events: kubectl describe pod <pod-name> -n retail")
        analysis.append("  3. Verify configuration and environment variables")
        analysis.append("  4. Consider increasing resources if under heavy load")
    
    return "\n".join(analysis)

def analyze_high_latency(logs, events):
    analysis = []
    recommendations = []
    
    analysis.append("High Latency Analysis")
    
    if any(term in logs.lower() for term in ["slow query", "timeout", "deadline exceeded"]):
        analysis.append("Database performance issues detected")
        recommendations.append("Check database connection pool size")
        recommendations.append("Review slow queries and add indexes")
    
    if "Throttling" in events or "CPU" in events:
        analysis.append("CPU throttling detected")
        recommendations.append("Increase CPU limits for the pod")
        recommendations.append("Consider horizontal pod autoscaling")
    
    if "OOMKilled" in events:
        analysis.append("Memory constraints may cause latency")
        recommendations.append("Increase memory limits")
    
    if any(term in logs.lower() for term in ["network", "connection pool", "retrying"]):
        analysis.append("Network connectivity issues")
        recommendations.append("Check network policies and service mesh configuration")
        recommendations.append("Verify DNS resolution and service endpoints")
    
    analysis.append("\nPerformance Recommendations:")
    if recommendations:
        for rec in recommendations:
            analysis.append(f"  - {rec}")
    else:
        analysis.append("  - Review application code for bottlenecks")
        analysis.append("  - Add caching for frequently accessed data")
        analysis.append("  - Consider implementing connection pooling")
        analysis.append("  - Profile application to identify slow endpoints")
    
    analysis.append("\nRemediation Steps:")
    analysis.append("  1. Scale the deployment: kubectl scale deployment <name> -n retail --replicas=3")
    analysis.append("  2. Add resource limits to prevent throttling")
    analysis.append("  3. Implement readiness/liveness probes for better traffic management")
    analysis.append("  4. Use kubectl top pods -n retail to check resource usage")
    
    return "\n".join(analysis)

def analyze_deployment_failure(pods_output, events_output):
    analysis = []
    
    analysis.append("Deployment Failure Analysis\n")
    
    if "CrashLoopBackOff" in pods_output:
        analysis.append("Deployment failed: Pods in CrashLoopBackOff")
        analysis.append("The application is crashing on startup")
    
    if "ImagePullBackOff" in pods_output or "ErrImagePull" in events_output:
        analysis.append("Deployment failed: Image pull issues")
        analysis.append("Kubernetes cannot pull the container image")
        analysis.append("\nRemediation:")
        analysis.append("  - Verify image name and tag in deployment YAML")
        analysis.append("  - Check image registry credentials (imagePullSecrets)")
        analysis.append("  - Ensure the image exists in the registry")
    
    if "Pending" in pods_output:
        analysis.append("Pods stuck in Pending state")
        if "Insufficient" in events_output:
            analysis.append("  - Resource constraints detected")
            analysis.append("Remediation: Add more nodes or reduce resource requests")
        else:
            analysis.append("Remediation: Check PVC binding, node selectors, and tolerations")
    
    if "Evicted" in pods_output:
        analysis.append("Pods being evicted")
        analysis.append("Nodes are under memory/disk pressure")
        analysis.append("Remediation: Increase node size or add more nodes")
    
    if "Failed" in events_output or "Error" in events_output:
        analysis.append("\nRecent Error Events:")
        events_lines = events_output.split('\n')
        error_events = [line for line in events_lines if "Failed" in line or "Error" in line]
        for event in error_events[:5]:
            analysis.append(f"  - {event}")
    
    analysis.append("\nGeneral Deployment Fixes:")
    analysis.append("  1. Check rollout status: kubectl rollout status deployment/<name> -n retail")
    analysis.append("  2. View deployment history: kubectl rollout history deployment/<name> -n retail")
    analysis.append("  3. Rollback if needed: kubectl rollout undo deployment/<name> -n retail")
    analysis.append("  4. Validate YAML: kubectl apply --dry-run=client -f deployment.yaml")
    
    return "\n".join(analysis)

def troubleshoot_pod_restart(pod_name):
    print(f"\nSCENARIO 1: Pod '{pod_name}' is restarting")
    print("-" * 50)
    
    logs = get_logs(pod_name)
    events = get_events(pod_name)
    pod_status = get_pod_status(pod_name)
    
    analysis = analyze_pod_restart(logs, events, pod_status)
    print(analysis)
    
    if logs and logs != "Error getting logs:":
        print(f"\nRecent Logs (first 20 lines):")
        log_lines = logs.split('\n')[:20]
        for line in log_lines:
            if line.strip():
                print(f"  {line[:150]}")

def troubleshoot_high_latency(pod_name):
    print(f"\nSCENARIO 2: High latency detected for '{pod_name}'")
    print("-" * 50)
    
    logs = get_logs(pod_name, lines=200)
    events = get_events(pod_name)
    
    analysis = analyze_high_latency(logs, events)
    print(analysis)

def troubleshoot_deployment_failure(namespace="retail"):
    print(f"\nSCENARIO 3: Deployment failure in namespace '{namespace}'")
    print("-" * 50)
    
    events = get_k8s_events(namespace, limit=30)
    pods = get_pods(namespace)
    
    analysis = analyze_deployment_failure(pods, events)
    print(analysis)

def verify_kubectl():
    try:
        result = subprocess.run(["kubectl", "version", "--client"], capture_output=True, text=True)
        if result.returncode == 0:
            print("kubectl is available")
            return True
        else:
            print("kubectl not found. Please install kubectl first.")
            return False
    except FileNotFoundError:
        print("kubectl not found. Please install kubectl first.")
        return False

def list_pods_in_namespace(namespace="retail"):
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "name"],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0 and result.stdout:
            pods = [p.split('/')[-1] for p in result.stdout.strip().split('\n') if p]
            return pods
        return []
    except Exception:
        return []

if __name__ == "__main__":
    print("\n" + "="*60)
    print("KUBERNETES TROUBLESHOOTING AGENT (API-FREE VERSION)")
    print("="*60)
    
    if not verify_kubectl():
        print("\nPlease install kubectl first: https://kubernetes.io/docs/tasks/tools/")
        exit(1)
    
    namespace = "retail"
    
    check_ns = subprocess.run(["kubectl", "get", "ns", namespace], capture_output=True, text=True)
    if check_ns.returncode != 0:
        print(f"\nNamespace '{namespace}' not found.")
        print("Creating namespace 'retail'...")
        subprocess.run(["kubectl", "create", "ns", namespace], capture_output=True)
    
    pods = list_pods_in_namespace(namespace)
    
    if not pods:
        print(f"\nNo pods found in '{namespace}' namespace.")
        print("The troubleshooting agent will run in demo mode with generic analysis.")
        pod_name = "demo-pod"
    else:
        userprofile_pods = [p for p in pods if 'userprofile' in p]
        if userprofile_pods:
            pod_name = userprofile_pods[0]
            print(f"\nFound pod: {pod_name}")
        else:
            pod_name = pods[0]
            print(f"\nFound pod: {pod_name}")
    
    troubleshoot_pod_restart(pod_name)
    
    print("\n" + "-" * 60)
    
    troubleshoot_high_latency(pod_name)
    
    print("\n" + "-" * 60)
    
    troubleshoot_deployment_failure(namespace)
    
    print("\n" + "="*60)
    print("Analysis completed successfully")
    print("="*60)
    
    print("\nHelpful Commands for Further Investigation:")
    print(f"  - kubectl get pods -n {namespace} -w")
    print(f"  - kubectl describe pod {pod_name} -n {namespace}")
    print(f"  - kubectl logs {pod_name} -n {namespace} --previous")
    print(f"  - kubectl top pods -n {namespace}")
    print(f"  - kubectl get events -n {namespace} --sort-by='.lastTimestamp'")

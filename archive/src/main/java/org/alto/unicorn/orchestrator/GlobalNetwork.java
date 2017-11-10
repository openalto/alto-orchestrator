package org.alto.unicorn.orchestrator;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class GlobalNetwork {

	private static List<String> domains = new LinkedList<String>();
	
	private static List<String> hosts = new LinkedList<String>();
	
	private static Map<String, String> host2Domain = new HashMap<String, String>();
	
	private static Map<String, String> ingressPoint2Domain = new HashMap<String, String>();
	
	public static void setup() {
		domains.add("10.0.0.1");
		domains.add("10.0.0.2");
		domains.add("10.0.0.3");
		domains.add("10.0.0.4");
		
		hosts.add("192.168.0.1");
		hosts.add("192.168.0.2");
		hosts.add("192.168.0.3");
		hosts.add("192.168.0.4");
		
		host2Domain.put("192.168.0.1", "10.0.0.1");
		host2Domain.put("192.168.0.2", "10.0.0.1");
		host2Domain.put("192.168.0.3", "10.0.0.1");
		host2Domain.put("192.168.0.4", "10.0.0.1");
		
		ingressPoint2Domain.put("10.0.2.1", "10.0.0.2");
		ingressPoint2Domain.put("10.0.3.1", "10.0.0.3");
		ingressPoint2Domain.put("10.0.4.1", "10.0.0.4");
		ingressPoint2Domain.put("10.0.4.2", "10.0.0.4");
	}
	
	// file: host(ip address) domain(ip address)
	private static void setupDomainsHosts(String fileName) {
		
	}
	
	// file: ingress-point(ip address) domain(ip address)
	private static void setupIngressPoints(String fileName) {
		
	}
	
	public static String getDomainByHost(String hostIP) {
		return host2Domain.get(hostIP);
	}
	
	public static String getDomainByIngressPoint(String ingressPoint) {
		return ingressPoint2Domain.get(ingressPoint);
	}
}

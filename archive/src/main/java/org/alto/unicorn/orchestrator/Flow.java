package org.alto.unicorn.orchestrator;

public class Flow {

	private String srcIp;
	
	private String dstIp;
	
	private int dstPort;
	
	private String protocol;
	
	private String ingressPoint;
	
	public Flow(String srcIp, String dstIp, int dstPort, String protocol, String ingressPort) {
		this.srcIp = srcIp;
		this.dstIp = dstIp;
		this.dstPort = dstPort;
		this.protocol = protocol;
		this.ingressPoint = ingressPort;
	}

	public String getSrcIp() {
		return srcIp;
	}

	public void setSrcIp(String srcIp) {
		this.srcIp = srcIp;
	}

	public String getDstIp() {
		return dstIp;
	}

	public void setDstIp(String dstIp) {
		this.dstIp = dstIp;
	}

	public int getDstPort() {
		return dstPort;
	}

	public void setDstPort(int dstPort) {
		this.dstPort = dstPort;
	}

	public String getProtocol() {
		return protocol;
	}

	public void setProtocol(String protocol) {
		this.protocol = protocol;
	}

	public String getIngressPoint() {
		return ingressPoint;
	}

	public void setIngressPoint(String ingressPoint) {
		this.ingressPoint = ingressPoint;
	}
	
	@Override
	public String toString() {
		return "srcIP:" + this.srcIp + " dstIP:" + this.dstIp + 
				" dstPort:" + this.dstPort + " protocol:" + this.protocol + " ingressPort:" + this.ingressPoint;
	}
	
	@Override
	public int hashCode() {
		return this.toString().hashCode();
	}
}

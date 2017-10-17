package org.alto.unicorn.orchestrator;

import java.io.InputStream;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;

import com.mashape.unirest.http.HttpResponse;
import com.mashape.unirest.http.JsonNode;
import com.mashape.unirest.http.Unirest;
import com.mashape.unirest.http.async.Callback;
import com.mashape.unirest.http.exceptions.UnirestException;


public class PathQuery {
	
	class Token {
		
	}
	
	class PathRequest {
		String domain;
		
		List<Flow> flows;
		
		public PathRequest(String domain, List<Flow> flows) {
			this.domain = domain;
			this.flows = flows;
		}
	}
	
	class PathResponse {
		Map<Flow, String> flow2IngressPort;
		
		public PathResponse(Map<Flow, String> flow2IngressPort) {
			this.flow2IngressPort = flow2IngressPort;
		}
	}
	
	private BlockingQueue<Token> connectionQueue;
	
	private BlockingQueue<PathRequest> pathRequestQueue;
	
	private BlockingQueue<PathResponse> pathResponseQueue;
	
	private int tokenSize;
	
	private BlockingQueue<PathRequest> resultQueue;
	
	private ConcurrentHashMap<Flow, Boolean> finishedFlows;

	public PathQuery(int tokenSize) {
		connectionQueue = new LinkedBlockingQueue<PathQuery.Token>();
		pathRequestQueue = new LinkedBlockingQueue<PathQuery.PathRequest>();
		pathResponseQueue = new LinkedBlockingQueue<PathQuery.PathResponse>();
		resultQueue = new LinkedBlockingQueue<PathQuery.PathRequest>();
		this.tokenSize = tokenSize;
		
		finishedFlows = new ConcurrentHashMap<Flow, Boolean>();
		
		ExecutorService gb = Executors.newFixedThreadPool(1);
		ExecutorService wts = Executors.newFixedThreadPool(1);
		
		gb.submit(new GroupBy(pathResponseQueue, pathRequestQueue));
		wts.submit(new WaitToSend(pathRequestQueue, connectionQueue, pathResponseQueue, resultQueue));
		for (int i = 0; i < tokenSize; i++) {
			connectionQueue.add(new Token());
		}
		
		gb.shutdown();
		wts.shutdown();
		
	}
	
	class WaitToSend implements Runnable {
		private final BlockingQueue<PathRequest> pathRequestQueue;
		private final BlockingQueue<PathResponse> pathResponseQueue;
		private final BlockingQueue<Token> connectionQueue;
		private final BlockingQueue<PathRequest> resultQueue;
		
		public WaitToSend(BlockingQueue<PathRequest> pathRequestQueue, 
				BlockingQueue<Token> connectionQueue, 
				BlockingQueue<PathResponse> pathResponseQueue,
				BlockingQueue<PathRequest> resultQueue) {
			this.pathRequestQueue = pathRequestQueue;
			this.connectionQueue = connectionQueue;
			this.pathResponseQueue = pathResponseQueue;
			this.resultQueue = resultQueue;
		}

		public void run() {
			while(true) {
				try {
					System.out.println("PathQuery: WaitToSend: before take");
					PathRequest pRequest = pathRequestQueue.take();
					System.out.println("PathQuery: WaitToSend: after take");
					//Thread.sleep(100);
					resultQueue.add(pRequest);
					Token token = connectionQueue.take();
					dummySendRequest(pRequest);
					//sendRequest(pRequest);
					
				} catch (InterruptedException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				}
			}
		}
		
		private void dummySendRequest(PathRequest pathRequest) {
			String domain = pathRequest.domain;
			List<Flow> flows = pathRequest.flows;
			Map<Flow, String> flow2IngressPoint = new HashMap<Flow, String>();
			
			for (Flow f: flows) {
				if (domain.equals("10.0.0.1")) {
					if (f.getSrcIp().equals("192.168.0.1") && f.getIngressPoint().equals("")) {
						flow2IngressPoint.put(f, "10.0.2.1");
					} else if (f.getSrcIp().equals("192.168.0.2") && f.getIngressPoint().equals("")) {
						flow2IngressPoint.put(f, "10.0.2.1");
					} else if (f.getSrcIp().equals("192.168.0.3") && f.getIngressPoint().equals("")) {
						flow2IngressPoint.put(f, "10.0.3.1");
					} else if (f.getSrcIp().equals("192.168.0.4") && f.getIngressPoint().equals("")) {
						flow2IngressPoint.put(f, "10.0.3.1");
					}
				} else if (domain.equals("10.0.0.2")) {
					if (f.getSrcIp().equals("192.168.0.1") && f.getIngressPoint().equals("10.0.2.1")) {
						flow2IngressPoint.put(f, "10.0.4.1");
					} else if (f.getSrcIp().equals("192.168.0.2") && f.getIngressPoint().equals("10.0.2.1")) {
						flow2IngressPoint.put(f, "10.0.4.1");
					}
				} else if (domain.equals("10.0.0.3")) {
					if (f.getSrcIp().equals("192.168.0.3") && f.getIngressPoint().equals("10.0.3.1")) {
						flow2IngressPoint.put(f, "10.0.4.1");
					} else if (f.getSrcIp().equals("192.168.0.4") && f.getIngressPoint().equals("10.0.3.1")) {
						flow2IngressPoint.put(f, "10.0.4.1");
					}
				} else if (domain.equals("10.0.0.4")) {
					flow2IngressPoint.put(f, "");
				}
			}
			
			PathResponse pathResponse = new PathResponse(flow2IngressPoint);
			try {
				Thread.sleep(50);
			} catch (InterruptedException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
			connectionQueue.add(new Token());
			pathResponseQueue.add(pathResponse);
			checkFinishedFlows(pathResponse);
		}
		
		private void checkFinishedFlows(PathResponse pathResponse) {
			System.out.println("get response");
			for (Map.Entry<Flow, String> entry: pathResponse.flow2IngressPort.entrySet()) {
				System.out.println("flow: " + entry.getKey());
				System.out.println("ingress point: " + entry.getValue());
				String ingressPoint = entry.getValue();
				if (ingressPoint.equals("")) {
					finishedFlows.put(entry.getKey(), true);
				}
			}
		}
		
		private void sendRequest(PathRequest pathRequest) {
			String url = pathRequest.domain;
			Future<HttpResponse<JsonNode>> future = Unirest.post(url)
					  .header("accept", "application/json")
					  .field("param1", "value1")
					  .field("param2", "value2")
					  .asJsonAsync(new Callback<JsonNode>() {

					    public void failed(UnirestException e) {
					        System.out.println("The request has failed");
					    }

					    public void completed(HttpResponse<JsonNode> response) {
					         int code = response.getStatus();
					         JsonNode body = response.getBody();
					         InputStream rawBody = response.getRawBody();
					         connectionQueue.add(new Token());
					         pathResponseQueue.add(getPathResponse(body));
					    }

					    public void cancelled() {
					        System.out.println("The request has been cancelled");
					    }

					});
		}
		
		private PathResponse getPathResponse(JsonNode body) {
			return null;
		}
	}
	
	class GroupBy implements Runnable {
		private final BlockingQueue<PathResponse> pathResponseQueue;
		private final BlockingQueue<PathRequest> pathRequestQueue;
		
		public GroupBy(BlockingQueue<PathResponse> pathResponseQueue, BlockingQueue<PathRequest> pathRequestQueue) {
			this.pathResponseQueue = pathResponseQueue;
			this.pathRequestQueue = pathRequestQueue;
		}
		public void run() {
			while(true) {
				List<PathResponse> allPResponses = new LinkedList<PathQuery.PathResponse>();
				try {
					allPResponses.add(pathResponseQueue.take());
					System.out.println("PathQuery: GroupBy: run");
				} catch (InterruptedException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				}
				pathResponseQueue.drainTo(allPResponses);
				
				List<PathRequest> pathRequests = groupBy(allPResponses);
				pathRequestQueue.addAll(pathRequests);
			}
		}
		
		private List<PathRequest> groupBy(List<PathResponse> responses) {
			List<PathRequest> result = new LinkedList<PathQuery.PathRequest>();
			Map<String, List<Flow>> domain2Flows = new HashMap<String, List<Flow>>();
			for (PathResponse pResponse: responses) {
				for (Map.Entry<Flow, String> entry: pResponse.flow2IngressPort.entrySet()) {
					Flow flow = entry.getKey();
					String ingressPoint = entry.getValue();
					if (ingressPoint.equals("")) continue;
					String domain = GlobalNetwork.getDomainByIngressPoint(ingressPoint);
					Flow nextFlow = new Flow(flow.getSrcIp(), flow.getDstIp(), flow.getDstPort(),
							flow.getProtocol(), ingressPoint);
					if (domain2Flows.containsKey(domain)) {
						domain2Flows.get(domain).add(nextFlow);
					} else {
						List<Flow> tempFlows = new LinkedList<Flow>();
						tempFlows.add(nextFlow);
						domain2Flows.put(domain, tempFlows);
					}
				}
			}
			for (Map.Entry<String, List<Flow>> entry: domain2Flows.entrySet()) {
				PathRequest pRequest = new PathRequest(entry.getKey(), entry.getValue());
				result.add(pRequest);
			}
			return result;
		}
	}
	
	public Map<String, List<Flow>> getDomain2Flows(List<Flow> flows) {
		List<PathRequest> pRequests = firstFlows2PathRequests(flows);
		pathRequestQueue.addAll(pRequests);
		System.out.println("finish adding first path request, size: " + pathRequestQueue.size());
		
		while(finishedFlows.size() != flows.size()) {
			System.out.println("while");
			try {
				Thread.sleep(10);
			} catch (InterruptedException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
			
		}
		
		List<PathRequest> allPathRequests = new LinkedList<PathQuery.PathRequest>();
		this.resultQueue.drainTo(allPathRequests);
		return compressedPathQueryResult(allPathRequests);
	}
	
	private Map<String, List<Flow>> compressedPathQueryResult(List<PathRequest> pathRequests) {
		Map<String, List<Flow>> result = new HashMap<String, List<Flow>>();
		for (PathRequest pRequest: pathRequests) {
			String domain = pRequest.domain;
			List<Flow> flows = pRequest.flows;
			if (result.containsKey(domain)) {
				result.get(domain).addAll(flows);
			} else {
				List<Flow> tempFlows = new LinkedList<Flow>();
				tempFlows.addAll(flows);
				result.put(domain, tempFlows);
			}
		}
		return result;
	}
	
	private List<PathRequest> firstFlows2PathRequests(List<Flow> flows) {
		List<PathRequest> result = new LinkedList<PathQuery.PathRequest>();
		Map<String, List<Flow>> domain2Flows = new HashMap<String, List<Flow>>();
		for (Flow f: flows) {
			String domain = GlobalNetwork.getDomainByHost(f.getSrcIp());
			if (domain2Flows.containsKey(domain)) {
				domain2Flows.get(domain).add(f);
			} else {
				List<Flow> tempFlows = new LinkedList<Flow>();
				tempFlows.add(f);
				domain2Flows.put(domain, tempFlows);
			}
		}
		
		for (Map.Entry<String, List<Flow>> entry: domain2Flows.entrySet()) {
			String domain = entry.getKey();
			List<Flow> flowList = entry.getValue();
			PathRequest pathRequest = new PathRequest(domain, flowList);
			result.add(pathRequest);
		}
		return result;
	}
	
	public static void main(String[] args) {
		GlobalNetwork.setup();
		
		PathQuery pQuery = new PathQuery(4);
		List<Flow> flows = new LinkedList<Flow>();
		Flow f1 = new Flow("192.168.0.1", "4.4.4.4", 10, "tcp", "");
		Flow f2 = new Flow("192.168.0.2", "4.4.4.4", 10, "tcp", "");
		Flow f3 = new Flow("192.168.0.3", "4.4.4.4", 10, "tcp", "");
		Flow f4 = new Flow("192.168.0.4", "4.4.4.4", 10, "tcp", "");
		
		flows.add(f1);
		flows.add(f2);
		flows.add(f3);
		flows.add(f4);
		
		System.out.println("result: " + pQuery.getDomain2Flows(flows));
	}
}

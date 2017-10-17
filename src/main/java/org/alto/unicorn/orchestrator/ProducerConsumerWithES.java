package org.alto.unicorn.orchestrator;

import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.*;

public class ProducerConsumerWithES {
    public static void main(String args[]){
         BlockingQueue<Integer> sharedQueue = new LinkedBlockingQueue<Integer>();

         ExecutorService pes = Executors.newFixedThreadPool(2);
         ExecutorService ces = Executors.newFixedThreadPool(2);

         pes.submit(new Producer(sharedQueue,1));
         pes.submit(new Producer(sharedQueue,2));
         ces.submit(new Consumer(sharedQueue,1));
         ces.submit(new Consumer(sharedQueue,2));
         // shutdown should happen somewhere along with awaitTermination
         pes.shutdown();
         ces.shutdown();
         
         
         List<Producer> ppp1 = new LinkedList<Producer>();
         List<Producer> ppp2 = new LinkedList<Producer>();
         
         Producer p1 = new Producer(null, 1);
         ppp1.add(p1);
         ppp2.add(p1);
         ppp1.remove(0);
         System.out.println(ppp2.size());
    }
}
class Producer implements Runnable {
    private final BlockingQueue<Integer> sharedQueue;
    private int threadNo;
    public Producer(BlockingQueue<Integer> sharedQueue,int threadNo) {
        this.threadNo = threadNo;
        this.sharedQueue = sharedQueue;
    }
    @Override
    public void run() {
        for(int i=1; i<= 5; i++){
            try {
                int number = i+(10*threadNo);
                System.out.println("Produced:" + number + ":by thread:"+ threadNo);
                sharedQueue.put(number);
            } catch (Exception err) {
                err.printStackTrace();
            }
        }
    }
}

class Consumer implements Runnable{
    private final BlockingQueue<Integer> sharedQueue;
    private int threadNo;
    public Consumer (BlockingQueue<Integer> sharedQueue,int threadNo) {
        this.sharedQueue = sharedQueue;
        this.threadNo = threadNo;
    }
    @Override
    public void run() {
        while(true){
            try {
                int num = sharedQueue.take();
                System.out.println("Consumed: "+ num + ":by thread:"+threadNo);
            } catch (Exception err) {
               err.printStackTrace();
            }
        }
    }   
}
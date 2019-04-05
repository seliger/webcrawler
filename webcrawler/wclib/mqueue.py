import pika

class MessageQueue:

    mq_conn = None
    queues = {}

    def __init__(self, config):
        self.config = config
        if self.mq_conn is None:
            self.mq_conn = pika.BlockingConnection(pika.ConnectionParameters(host=config.mqueue['host']))

    def create_queue(self, queue_name, durable=True):
        self.config.logger.debug('Creating and connecting to queue %s and durable is %s.', queue_name, str(durable))
        self.queues[queue_name] = self.mq_conn.channel()
        self.queues[queue_name].queue_declare(queue=queue_name, durable=durable)

        return self.queues[queue_name]

    def destroy_queue(self, queue_name):
        self.config.logger.debug('Destroying connection to queue %s.', queue_name)
        self.queues[queue_name].close()
        del self.queues[queue_name]

    def queue_length(self, queue_name, durable=True):
        state = self.queues[queue_name].queue_declare(queue=queue_name, durable=durable)
        return state.method.message_count

    def queue_push(self, queue_name, payload):
        self.config.logger.debug("Pushing message '%s' onto queue '%s'.", payload, queue_name)
        self.queues[queue_name].basic_publish(exchange='', routing_key=queue_name, body=payload, properties=pika.BasicProperties(delivery_mode=2))

    def queue_listen(self, queue_name, callback):
        self.config.logger.debug("Starting listener '%s' for queue '%s'.", callback.__name__, queue_name)
        self.queues[queue_name].basic_consume(queue_name, callback)
        self.queues[queue_name].start_consuming()
    


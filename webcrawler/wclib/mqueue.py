import pika

class MessageQueue:

    mq_conn = None
    queues = {}

    def __init__(self, config):
        self.config = config
        if self.mq_conn is None:
            credentials = pika.PlainCredentials(config.mqueue['user'], config.mqueue['password'])
            parameters = pika.ConnectionParameters(config.mqueue['host'], config.mqueue['port'], config.mqueue['vhost'], credentials, heartbeat=600, blocked_connection_timeout=300)
            self.mq_conn = pika.BlockingConnection(parameters)

    def create_queue(self, queue_name, durable=True):
        self.config.logger.debug('Creating and connecting to queue %s and durable is %s.', queue_name, str(durable))
        self.queues[queue_name] = self.mq_conn.channel()
        self.queues[queue_name].queue_declare(queue=queue_name, durable=durable)

        return self.queues[queue_name]

    def destroy_conn(self):
        self.config.logger.debug('Destroying connection to message broker.')
        self.mq_conn.close()
        self.queues = {}

    def destroy_queue(self, queue_name):
        self.config.logger.debug('Destroying connection to queue %s.', queue_name)
        self.queues[queue_name].close()
        del self.queues[queue_name]

    def queue_length(self, queue_name, durable=True):
        state = self.queues[queue_name].queue_declare(queue=queue_name, durable=durable)
        return state.method.message_count

    def queue_push(self, queue_name, payload):
        #self.config.logger.debug("Pushing message '%s' onto queue '%s'.", payload, queue_name)
        self.queues[queue_name].basic_publish(exchange='', routing_key=queue_name, body=payload, properties=pika.BasicProperties(delivery_mode=2))

    def queue_consume(self, queue_name, callback):
        self.config.logger.debug("Starting consumer '%s' for queue '%s'.", callback.__name__, queue_name)
        self.queues[queue_name].basic_qos(prefetch_count=1)
        self.queues[queue_name].basic_consume(queue_name, callback)
        self.queues[queue_name].start_consuming()

    def queue_stop_consuming(self, queue_name):
        self.config.logger.debug("Stopping consumer for queue '%s'.", queue_name)
        self.queues[queue_name].stop_consuming()
    


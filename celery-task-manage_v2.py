import os
from celery import Celery
from kombu import Connection
import json
from datetime import datetime

# Initialize Celery app
app = Celery('queue_manager')

# Configure broker (Redis example - adjust for your setup)
BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.conf.broker_url = BROKER_URL

class CeleryQueueManager:
    def __init__(self, broker_url=None):
        self.broker_url = broker_url or BROKER_URL
        self.connection = Connection(self.broker_url)
    
    def get_queue_info(self, queue_name='celery'):
        """Get information about a specific queue"""
        try:
            with self.connection.channel() as channel:
                queue = channel.queue_declare(queue=queue_name, passive=True)
                message_count = queue.method.message_count
                consumer_count = queue.method.consumer_count
                
                return {
                    'queue_name': queue_name,
                    'message_count': message_count,
                    'consumer_count': consumer_count,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {'error': str(e)}
    
    def list_all_queues(self):
        """List all available queues"""
        try:
            with self.connection.channel() as channel:
                # This method varies by broker type
                if 'redis' in self.broker_url:
                    return self._list_redis_queues()
                elif 'rabbitmq' in self.broker_url or 'amqp' in self.broker_url:
                    return self._list_rabbitmq_queues(channel)
                else:
                    return {'error': 'Unsupported broker type'}
        except Exception as e:
            return {'error': str(e)}
    
    def get_redis_queue_length(self, queue_name='celery'):
        """Get the actual length of a Celery queue in Redis"""
        import redis
        try:
            redis_client = redis.from_url(self.broker_url)
            # Celery uses lists for queues in Redis
            queue_key = queue_name
            
            # Try different possible queue key formats
            possible_keys = [
                queue_name,
                f"celery:{queue_name}",
                f"{queue_name}:queue",
                f"celery:queue:{queue_name}"
            ]
            
            for key in possible_keys:
                if redis_client.exists(key):
                    key_type = redis_client.type(key)
                    if isinstance(key_type, bytes):
                        key_type = key_type.decode('utf-8')
                    
                    if key_type == 'list':
                        length = redis_client.llen(key)
                        return {
                            'queue_name': queue_name,
                            'key': key,
                            'length': length,
                            'type': key_type
                        }
            
            return {
                'queue_name': queue_name,
                'length': 0,
                'message': 'Queue not found or empty'
            }
        except Exception as e:
            return {'error': str(e)}
        """List Redis queues"""
        import redis
        try:
            redis_client = redis.from_url(self.broker_url)
            keys = redis_client.keys('celery*')
            queues = []
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                
                # Check the type of the key and get appropriate length
                key_type = redis_client.type(key)
                if isinstance(key_type, bytes):
                    key_type = key_type.decode('utf-8')
                
                length = 0
                if key_type == 'list':
                    length = redis_client.llen(key)
                elif key_type == 'set':
                    length = redis_client.scard(key)
                elif key_type == 'zset':
                    length = redis_client.zcard(key)
                elif key_type == 'hash':
                    length = redis_client.hlen(key)
                elif key_type == 'string':
                    length = 1  # String keys have length 1 (one value)
                
                queues.append({
                    'name': key, 
                    'length': length,
                    'type': key_type
                })
            return queues
        except Exception as e:
            return {'error': str(e)}
    
    def _list_rabbitmq_queues(self, channel):
        """List RabbitMQ queues"""
        # Note: This requires management plugin for full functionality
        # Basic implementation - you might need to adapt based on your setup
        common_queues = ['celery', 'celery.priority', 'celery.high', 'celery.low']
        queues = []
        for queue_name in common_queues:
            try:
                queue = channel.queue_declare(queue=queue_name, passive=True)
                queues.append({
                    'name': queue_name,
                    'messages': queue.method.message_count,
                    'consumers': queue.method.consumer_count
                })
            except:
                continue
        return queues
    
    def peek_messages(self, queue_name='celery', count=10):
        """Peek at messages in queue without removing them"""
        try:
            with self.connection.channel() as channel:
                messages = []
                queue = channel.queue_declare(queue=queue_name, passive=True)
                
                # Get messages without acknowledging them
                for _ in range(min(count, queue.method.message_count)):
                    msg = channel.basic_get(queue=queue_name, no_ack=False)
                    if msg:
                        try:
                            body = json.loads(msg.body.decode('utf-8'))
                            messages.append({
                                'delivery_tag': msg.delivery_tag,
                                'task_id': body.get('id', 'unknown'),
                                'task_name': body.get('task', 'unknown'),
                                'args': body.get('args', []),
                                'kwargs': body.get('kwargs', {}),
                                'eta': body.get('eta'),
                                'expires': body.get('expires')
                            })
                        except:
                            messages.append({
                                'delivery_tag': msg.delivery_tag,
                                'raw_body': msg.body.decode('utf-8', errors='ignore')
                            })
                        
                        # Reject message to put it back in queue
                        channel.basic_nack(msg.delivery_tag, requeue=True)
                    else:
                        break
                
                return messages
        except Exception as e:
            return {'error': str(e)}
    
    def delete_message_by_id(self, task_id, queue_name='celery'):
        """Delete a specific message by task ID"""
        try:
            with self.connection.channel() as channel:
                deleted = False
                processed = 0
                
                while True:
                    msg = channel.basic_get(queue=queue_name, no_ack=False)
                    if not msg:
                        break
                    
                    processed += 1
                    try:
                        body = json.loads(msg.body.decode('utf-8'))
                        if body.get('id') == task_id:
                            # Acknowledge to delete the message
                            channel.basic_ack(msg.delivery_tag)
                            deleted = True
                            break
                        else:
                            # Reject to put back in queue
                            channel.basic_nack(msg.delivery_tag, requeue=True)
                    except:
                        # If we can't parse, put it back
                        channel.basic_nack(msg.delivery_tag, requeue=True)
                
                return {
                    'deleted': deleted,
                    'task_id': task_id,
                    'processed_messages': processed
                }
        except Exception as e:
            return {'error': str(e)}
    
    def purge_queue(self, queue_name='celery'):
        """Delete all messages in a queue"""
        try:
            with self.connection.channel() as channel:
                result = channel.queue_purge(queue=queue_name)
                return {
                    'queue_name': queue_name,
                    'messages_deleted': result,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {'error': str(e)}
    
    def purge_redis_queue(self, queue_name='celery'):
        """Purge a specific Redis queue used by Celery"""
        import redis
        try:
            redis_client = redis.from_url(self.broker_url)
            
            # Try different possible queue key formats
            possible_keys = [
                queue_name,
                f"celery:{queue_name}",
                f"{queue_name}:queue",
                f"celery:queue:{queue_name}"
            ]
            
            deleted_count = 0
            for key in possible_keys:
                if redis_client.exists(key):
                    key_type = redis_client.type(key)
                    if isinstance(key_type, bytes):
                        key_type = key_type.decode('utf-8')
                    
                    if key_type == 'list':
                        length = redis_client.llen(key)
                        redis_client.delete(key)
                        deleted_count += length
                        
            return {
                'queue_name': queue_name,
                'messages_deleted': deleted_count,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
        """Delete all messages for a specific task type"""
        try:
            with self.connection.channel() as channel:
                deleted_count = 0
                processed = 0
                
                while True:
                    msg = channel.basic_get(queue=queue_name, no_ack=False)
                    if not msg:
                        break
                    
                    processed += 1
                    try:
                        body = json.loads(msg.body.decode('utf-8'))
                        if body.get('task') == task_name:
                            # Acknowledge to delete the message
                            channel.basic_ack(msg.delivery_tag)
                            deleted_count += 1
                        else:
                            # Reject to put back in queue
                            channel.basic_nack(msg.delivery_tag, requeue=True)
                    except:
                        # If we can't parse, put it back
                        channel.basic_nack(msg.delivery_tag, requeue=True)
                
                return {
                    'task_name': task_name,
                    'deleted_count': deleted_count,
                    'processed_messages': processed,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {'error': str(e)}

# Usage examples
def main():
    # Initialize queue manager
    queue_manager = CeleryQueueManager()
    
    # Check queue info
    print("=== Queue Information ===")
    info = queue_manager.get_queue_info('celery')
    print(json.dumps(info, indent=2))
    
    # For Redis, get more specific queue info
    print("\n=== Redis Queue Length ===")
    redis_info = queue_manager.get_redis_queue_length('celery')
    print(json.dumps(redis_info, indent=2))
    
    # List all queues
    print("\n=== All Queues ===")
    queues = queue_manager.list_all_queues()
    print(json.dumps(queues, indent=2))
    
    # Peek at messages
    print("\n=== Peek Messages ===")
    messages = queue_manager.peek_messages('celery', count=5)
    print(json.dumps(messages, indent=2))
    
    # Delete specific message by ID
    # task_id = "your-task-id-here"
    # result = queue_manager.delete_message_by_id(task_id)
    # print(f"Delete result: {result}")
    
    # Delete messages by task name
    # result = queue_manager.delete_messages_by_task_name('myapp.tasks.process_data')
    # print(f"Delete by task name result: {result}")
    
    # Purge entire queue (use with caution!)
    # result = queue_manager.purge_queue('celery')
    # print(f"Purge result: {result}")
    
    # For Redis, use specific purge method
    # result = queue_manager.purge_redis_queue('celery')
    # print(f"Redis purge result: {result}")

# CLI interface
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Celery Queue Manager')
    parser.add_argument('--action', choices=['info', 'list', 'peek', 'delete-id', 'delete-task', 'purge'], 
                       required=True, help='Action to perform')
    parser.add_argument('--queue', default='celery', help='Queue name')
    parser.add_argument('--task-id', help='Task ID to delete')
    parser.add_argument('--task-name', help='Task name to delete')
    parser.add_argument('--count', type=int, default=10, help='Number of messages to peek')
    
    args = parser.parse_args()
    
    queue_manager = CeleryQueueManager()
    
    if args.action == 'info':
        result = queue_manager.get_queue_info(args.queue)
    elif args.action == 'list':
        result = queue_manager.list_all_queues()
    elif args.action == 'peek':
        result = queue_manager.peek_messages(args.queue, args.count)
    elif args.action == 'delete-id':
        if not args.task_id:
            print("Error: --task-id is required for delete-id action")
            sys.exit(1)
        result = queue_manager.delete_message_by_id(args.task_id, args.queue)
    elif args.action == 'delete-task':
        if not args.task_name:
            print("Error: --task-name is required for delete-task action")
            sys.exit(1)
        result = queue_manager.delete_messages_by_task_name(args.task_name, args.queue)
    elif args.action == 'purge':
        confirm = input(f"Are you sure you want to purge queue '{args.queue}'? (yes/no): ")
        if confirm.lower() == 'yes':
            result = queue_manager.purge_queue(args.queue)
        else:
            print("Purge cancelled")
            sys.exit(0)
    
    print(json.dumps(result, indent=2))

Key Features:
Queue Inspection:

Check queue information (message count, consumer count)
List all available queues
Peek at messages without removing them

Message Deletion:

Delete specific messages by task ID
Delete all messages of a specific task type
Purge entire queues

Usage Examples:
bash# Check queue info
python queue_manager.py --action info --queue celery

# List all queues
python queue_manager.py --action list

# Peek at messages
python queue_manager.py --action peek --queue celery --count 5

# Delete specific task by ID
python queue_manager.py --action delete-id --task-id "abc123" --queue celery

# Delete all messages for a task type
python queue_manager.py --action delete-task --task-name "myapp.tasks.process_data"

# Purge entire queue
python queue_manager.py --action purge --queue celery
Requirements:
bashpip install celery kombu redis  # or rabbitmq dependencies
Configuration:
Set your broker URL as an environment variable:
bashexport CELERY_BROKER_URL="redis://localhost:6379/0"
# or
export CELERY_BROKER_URL="amqp://guest@localhost//"
The code handles both Redis and RabbitMQ brokers and includes error handling for safe queue operations. Use the purge function carefully as it permanently deletes all messages in a queue.

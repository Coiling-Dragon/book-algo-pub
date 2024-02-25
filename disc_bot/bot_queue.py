import asyncio


class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class SingletonQueue(metaclass=SingletonMeta):
    book_data_queue = asyncio.Queue()
    alert_queue = asyncio.Queue()
    error_queue = asyncio.Queue()

    async def enqueue_book_data(self, message: str):
        await self.book_data_queue.put(message)

    async def dequeue_book_data(self) -> str:
        msg = await self.book_data_queue.get()
        self.book_data_queue.task_done()
        return msg

    async def enqueue_alert(self, message: str):
        print(f'Enqueuing alert: {message}')
        await self.alert_queue.put(message)

    async def dequeue_alert(self) -> str:
        msg = await self.alert_queue.get()
        self.alert_queue.task_done()
        return msg

    async def enqueue_error(self, message: str):
        await self.error_queue.put(message)

    async def dequeue_error(self) -> str:
        msg = await self.error_queue.get()
        self.error_queue.task_done()
        return msg

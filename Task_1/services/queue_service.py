import heapq

class QueueService:
    def __init__(self):
        self.queue = []
        self.counter = 0 

    def add_user(self, user, priority):
        heapq.heappush(self.queue, (priority, self.counter, user))
        self.counter += 1 

    def get_next_user(self):
        if self.queue:
            return heapq.heappop(self.queue)[2]
        return None
from collections import deque
import time

# circular queue using deque, should work fine
class CircularQueue:
    def __init__(self, capacity=None):
        self.capacity = capacity
        self._items = deque()

    def enqueue(self, item):
        if self.capacity is not None and len(self._items) >= self.capacity:
            raise OverflowError("CircularQueue is full")
        self._items.append(item)

    def dequeue(self):
        if self.is_empty():
            raise IndexError("CircularQueue is empty")
        return self._items.popleft()

    def is_empty(self):
        return len(self._items) == 0

    def __len__(self):
        return len(self._items)


# timing wheel for handling booking expiry
# ref: https://blog.acolyer.org/2015/11/23/hashed-and-hierarchical-timing-wheels/
class HierarchicalTimingWheel:
    def __init__(self, tick_seconds=1, second_slots=60, minute_slots=60):
        self.tick_seconds = tick_seconds
        self.second_slots = second_slots
        self.minute_slots = minute_slots
        self.current_time = int(time.time())
        self.second_hand = self.current_time % self.second_slots
        self.minute_hand = (self.current_time // self.second_slots) % self.minute_slots
        self.second_wheel = [CircularQueue() for _ in range(self.second_slots)]
        self.minute_wheel = [CircularQueue() for _ in range(self.minute_slots)]
        print("timing wheel initialized")

    def schedule(self, item, delay_seconds):
        delay_seconds = max(0, int(delay_seconds))
        task = {
          "item": item,
          "due_at": self.current_time + delay_seconds,
        }

        if delay_seconds < self.second_slots:
            secondSlot = (self.second_hand + delay_seconds) % self.second_slots
            self.second_wheel[secondSlot].enqueue(task)
            return

        minuteOffset = delay_seconds // self.second_slots
        minuteSlot = (self.minute_hand + minuteOffset) % self.minute_slots
        self.minute_wheel[minuteSlot].enqueue(task)

    def advance_to_now(self):
        now = int(time.time())
        if now <= self.current_time:
            return []

        due_items = []
        elapsed_seconds = now - self.current_time
        for _ in range(elapsed_seconds):
            due_items.extend(self._tick())
        return due_items

    def _tick(self):
        self.current_time += self.tick_seconds
        self.second_hand = (self.second_hand + 1) % self.second_slots
        due_items = []

        if self.second_hand == 0:
            self.minute_hand = (self.minute_hand + 1) % self.minute_slots
            self._cascade_minute_slot()

        bucket = self.second_wheel[self.second_hand]
        bucketSize = len(bucket)
        for _ in range(bucketSize):
            task = bucket.dequeue()
            if task["due_at"] <= self.current_time:
                due_items.append(task["item"])
            else:
                self._reschedule_task(task)

        return due_items

    def _cascade_minute_slot(self):
        bucket = self.minute_wheel[self.minute_hand]
        bucketSize = len(bucket)
        for _ in range(bucketSize):
            task = bucket.dequeue()
            self._reschedule_task(task)

    def _reschedule_task(self, task):
        remaining_seconds = max(0, int(task["due_at"] - self.current_time))

        if remaining_seconds < self.second_slots:
            secondSlot = (self.second_hand + remaining_seconds) % self.second_slots
            self.second_wheel[secondSlot].enqueue(task)
            return

        minuteOffset = remaining_seconds // self.second_slots
        minuteSlot = (self.minute_hand + minuteOffset) % self.minute_slots
        self.minute_wheel[minuteSlot].enqueue(task)

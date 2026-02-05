import json
import os

class TodoList:
    def __init__(self, filename='todo.json'):
        self.filename = filename
        self.tasks = self.load_tasks()

    def load_tasks(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def save_tasks(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=4, ensure_ascii=False)

    def add_task(self, task):
        self.tasks.append({"task": task, "completed": False})
        self.save_tasks()
        print(f"已添加任务: {task}")

    def list_tasks(self):
        if not self.tasks:
            print("当前没有任务。")
            return
        for i, task in enumerate(self.tasks, 1):
            status = "√" if task['completed'] else "×"
            print(f"{i}. [{status}] {task['task']}")

    def complete_task(self, index):
        if 0 < index <= len(self.tasks):
            self.tasks[index-1]['completed'] = True
            self.save_tasks()
            print(f"已完成任务: {self.tasks[index-1]['task']}")
        else:
            print("无效的任务索引。")

    def delete_task(self, index):
        if 0 < index <= len(self.tasks):
            removed = self.tasks.pop(index-1)
            self.save_tasks()
            print(f"已删除任务: {removed['task']}")
        else:
            print("无效的任务索引。")

def main():
    todo = TodoList()
    while True:
        print("
--- Python Todo List ---")
        print("1. 添加任务")
        print("2. 查看任务")
        print("3. 完成任务")
        print("4. 删除任务")
        print("5. 退出")
        
        choice = input("请选择操作 (1-5): ")
        
        if choice == '1':
            task = input("输入任务内容: ")
            todo.add_task(task)
        elif choice == '2':
            todo.list_tasks()
        elif choice == '3':
            todo.list_tasks()
            index = int(input("输入要完成的任务编号: "))
            todo.complete_task(index)
        elif choice == '4':
            todo.list_tasks()
            index = int(input("输入要删除的任务编号: "))
            todo.delete_task(index)
        elif choice == '5':
            break
        else:
            print("无效选择，请重试。")

if __name__ == "__main__":
    main()

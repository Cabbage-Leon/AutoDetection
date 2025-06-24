#!/usr/bin/env python3
"""
测试任务管理功能
"""

import sys
import os
import time
import requests
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_task_manager():
    """测试任务管理功能"""
    print("🧪 测试任务管理功能")
    print("=" * 50)
    
    base_url = "http://localhost:5000/seckill"
    
    try:
        # 1. 测试调度器状态
        print("1. 测试调度器状态...")
        response = requests.get(f"{base_url}/api/scheduler/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 调度器状态: {data.get('data', {}).get('status', 'unknown')}")
        else:
            print(f"   ❌ 获取调度器状态失败: {response.status_code}")
        
        # 2. 启动调度器
        print("\n2. 启动调度器...")
        response = requests.post(f"{base_url}/api/scheduler/start")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ 调度器启动成功")
            else:
                print(f"   ⚠️  调度器启动失败: {data.get('message')}")
        else:
            print(f"   ❌ 启动调度器失败: {response.status_code}")
        
        # 3. 创建测试任务
        print("\n3. 创建测试任务...")
        from datetime import datetime, timedelta
        
        task_data = {
            "name": "测试任务",
            "url": "https://www.baidu.com",
            "target_selector": "#su",
            "target_type": "css",
            "execution_time": (datetime.now() + timedelta(seconds=30)).isoformat(),
            "frequency": 5,
            "max_attempts": 3,
            "timezone": "Asia/Shanghai"
        }
        
        response = requests.post(
            f"{base_url}/api/tasks",
            headers={"Content-Type": "application/json"},
            data=json.dumps(task_data)
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                task_id = data.get('data', {}).get('task_id')
                print(f"   ✅ 任务创建成功，ID: {task_id}")
                
                # 4. 获取任务列表
                print("\n4. 获取任务列表...")
                response = requests.get(f"{base_url}/api/tasks")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        tasks = data.get('data', [])
                        print(f"   ✅ 获取到 {len(tasks)} 个任务")
                        for task in tasks:
                            print(f"      - {task.get('name')}: {task.get('status')}")
                    else:
                        print(f"   ❌ 获取任务列表失败: {data.get('message')}")
                else:
                    print(f"   ❌ 获取任务列表失败: {response.status_code}")
                
                # 5. 启动任务
                print(f"\n5. 启动任务 {task_id}...")
                response = requests.post(f"{base_url}/api/tasks/{task_id}/start")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print("   ✅ 任务启动成功")
                    else:
                        print(f"   ⚠️  任务启动失败: {data.get('message')}")
                else:
                    print(f"   ❌ 启动任务失败: {response.status_code}")
                
                # 6. 监控任务状态
                print("\n6. 监控任务状态...")
                for i in range(10):
                    response = requests.get(f"{base_url}/api/tasks/{task_id}")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            task = data.get('data', {})
                            status = task.get('status', 'unknown')
                            attempts = task.get('attempts', 0)
                            max_attempts = task.get('max_attempts', 0)
                            success_count = task.get('success_count', 0)
                            
                            print(f"   第{i+1}秒: {status} | 尝试: {attempts}/{max_attempts} | 成功: {success_count}")
                            
                            if attempts >= max_attempts:
                                print("   任务已完成")
                                break
                        else:
                            print(f"   第{i+1}秒: 获取任务状态失败")
                    else:
                        print(f"   第{i+1}秒: 请求失败")
                    
                    time.sleep(1)
                
                # 7. 停止任务
                print(f"\n7. 停止任务 {task_id}...")
                response = requests.post(f"{base_url}/api/tasks/{task_id}/stop")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print("   ✅ 任务停止成功")
                    else:
                        print(f"   ⚠️  任务停止失败: {data.get('message')}")
                else:
                    print(f"   ❌ 停止任务失败: {response.status_code}")
                
                # 8. 删除任务
                print(f"\n8. 删除任务 {task_id}...")
                response = requests.delete(f"{base_url}/api/tasks/{task_id}")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print("   ✅ 任务删除成功")
                    else:
                        print(f"   ⚠️  任务删除失败: {data.get('message')}")
                else:
                    print(f"   ❌ 删除任务失败: {response.status_code}")
                
            else:
                print(f"   ❌ 任务创建失败: {data.get('message')}")
        else:
            print(f"   ❌ 创建任务失败: {response.status_code}")
        
        # 9. 停止调度器
        print("\n9. 停止调度器...")
        response = requests.post(f"{base_url}/api/scheduler/stop")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("   ✅ 调度器停止成功")
            else:
                print(f"   ⚠️  调度器停止失败: {data.get('message')}")
        else:
            print(f"   ❌ 停止调度器失败: {response.status_code}")
        
        print("\n" + "=" * 50)
        print("🎉 任务管理功能测试完成！")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Flask应用，请确保应用正在运行")
        print("   运行命令: python run.py")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_task_manager() 
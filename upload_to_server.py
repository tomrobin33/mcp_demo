import paramiko
import os
import sys

def upload_to_static_server(local_file, remote_file, hostname, username, password, port=22):
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.put(local_file, remote_file)
    sftp.close()
    transport.close()
    print(f"上传完成: {remote_file}")
    print(f"公网下载链接：http://{hostname}:8001/{os.path.basename(local_file)}")

if __name__ == "__main__":
    # 支持命令行参数：python upload_to_server.py 本地文件 [远程文件名]
    if len(sys.argv) < 2:
        print("用法: python upload_to_server.py 本地文件 [远程文件名]")
        sys.exit(1)
    local_file = sys.argv[1]
    if not os.path.exists(local_file):
        print(f"本地文件不存在: {local_file}")
        sys.exit(1)
    # 远程文件名可选，默认与本地文件同名
    remote_filename = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(local_file)
    remote_path = f"/root/files/{remote_filename}"
    # 服务器信息（如需安全可用环境变量/密钥管理）
    hostname = "8.156.74.79"
    username = "root"
    password = "zfsZBC123."
    upload_to_static_server(local_file, remote_path, hostname, username, password) 
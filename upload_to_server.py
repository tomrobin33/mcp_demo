import paramiko
import os
import sys
import logging

logger = logging.getLogger("upload_debug")
logging.basicConfig(level=logging.INFO)

def upload_to_static_server(local_file, remote_file, hostname, username, password, port=22):
    # 1. 检查本地文件是否存在
    if not os.path.exists(local_file):
        logger.error(f"本地文件不存在: {local_file}")
        return False
    # 2. 检查本地文件是否可读
    try:
        with open(local_file, "rb") as f:
            f.read(1)
        logger.info(f"本地文件可正常打开: {local_file}")
    except Exception as e:
        logger.error(f"本地文件无法打开: {local_file}, 错误: {e}")
        return False
    # 3. 上传文件
    transport = paramiko.Transport((hostname, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        sftp.put(local_file, remote_file)
        logger.info(f"上传成功: {remote_file}")
        # 4. 检查远程文件是否存在
        try:
            sftp.stat(remote_file)
            logger.info(f"远程服务器已存在文件: {remote_file}")
        except FileNotFoundError:
            logger.error(f"远程服务器未找到文件: {remote_file}")
            return False
        # 5. ls远程目录内容
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, username=username, password=password)
            remote_dir = os.path.dirname(remote_file)
            stdin, stdout, stderr = ssh.exec_command(f"ls -l {remote_dir}")
            logger.info(f"远程目录({remote_dir})内容:\n" + stdout.read().decode())
            ssh.close()
        except Exception as e:
            logger.warning(f"远程ls目录失败: {e}")
    except Exception as e:
        logger.error(f"上传失败: {e}")
        return False
    finally:
        sftp.close()
        transport.close()
    print(f"上传完成: {remote_file}")
    print(f"公网下载链接：http://{hostname}:8001/{os.path.basename(local_file)}")
    return True

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
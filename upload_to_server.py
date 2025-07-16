import paramiko
import os

# 配置参数
hostname = "8.156.74.79"
port = 22
username = "root"
password = "zfsZBC123."
local_file = "output_1752654963.docx"  # 使用上次生成的文件
remote_path = f"/root/files/{os.path.basename(local_file)}"

# 上传文件
transport = paramiko.Transport((hostname, port))
transport.connect(username=username, password=password)
sftp = paramiko.SFTPClient.from_transport(transport)
if sftp is not None:
    sftp.put(local_file, remote_path)
    sftp.close()
transport.close()

print("上传完成！公网下载链接：")
print(f"http://8.156.74.79:8001/{os.path.basename(local_file)}") 
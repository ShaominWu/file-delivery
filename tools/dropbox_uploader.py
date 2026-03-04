"""
Dropbox 上传模块 - 小豆豆文件传送系统
"""
import os
import dropbox
from dropbox.files import WriteMode
from dropbox.sharing import SharedLinkSettings, RequestedVisibility

class DropboxUploader:
    def __init__(self, access_token=None):
        """初始化 Dropbox 上传器"""
        # 从环境变量或配置文件获取 token
        self.access_token = access_token or os.environ.get('DROPBOX_ACCESS_TOKEN')
        if not self.access_token:
            # 尝试从配置文件读取
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'dropbox_token.txt')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.access_token = f.read().strip()
        
        self.dbx = None
        if self.access_token:
            self.dbx = dropbox.Dropbox(self.access_token)
    
    def is_authenticated(self):
        """检查是否已认证"""
        if not self.dbx:
            return False
        try:
            # 测试连接
            self.dbx.users_get_current_account()
            return True
        except:
            return False
    
    def get_or_create_folder(self, folder_path):
        """获取或创建文件夹"""
        try:
            # 尝试获取文件夹
            self.dbx.files_get_metadata(folder_path)
            return folder_path
        except dropbox.exceptions.ApiError as e:
            # 文件夹不存在，创建它
            if isinstance(e.error, dropbox.files.GetMetadataError) and e.error.is_path():
                try:
                    self.dbx.files_create_folder_v2(folder_path)
                    return folder_path
                except Exception as create_error:
                    print(f"❌ 创建 Dropbox 文件夹失败: {create_error}")
                    return None
            return None
    
    def upload_file(self, local_path, dropbox_path):
        """
        上传文件到 Dropbox
        返回: (file_id, error)
        """
        if not self.dbx:
            return None, "Dropbox 未认证"
        
        try:
            file_size = os.path.getsize(local_path)
            filename = os.path.basename(local_path)
            
            # 确保目标文件夹存在
            folder_path = os.path.dirname(dropbox_path)
            if folder_path and folder_path != '/':
                self.get_or_create_folder(folder_path)
            
            # 上传文件
            with open(local_path, 'rb') as f:
                if file_size <= 150 * 1024 * 1024:  # 150MB 以下用普通上传
                    result = self.dbx.files_upload(
                        f.read(),
                        dropbox_path,
                        mode=WriteMode('overwrite')
                    )
                else:  # 大文件用分块上传
                    # 简单起见，先不支持大文件分块上传
                    result = self.dbx.files_upload(
                        f.read(),
                        dropbox_path,
                        mode=WriteMode('overwrite')
                    )
            
            return result.id, None
            
        except Exception as e:
            return None, str(e)
    
    def create_share_link(self, dropbox_path, password=None):
        """
        创建分享链接
        返回: (share_url, error)
        """
        if not self.dbx:
            return None, "Dropbox 未认证"
        
        try:
            # 设置分享链接为公开可访问
            settings = SharedLinkSettings(
                requested_visibility=RequestedVisibility('public')
            )
            
            # 创建分享链接
            try:
                link = self.dbx.sharing_create_shared_link_with_settings(
                    dropbox_path,
                    settings=settings
                )
            except dropbox.exceptions.ApiError as e:
                # 如果链接已存在，获取现有链接
                if 'shared_link_already_exists' in str(e):
                    links = self.dbx.sharing_list_shared_links(
                        path=dropbox_path,
                        direct_only=True
                    )
                    if links.links:
                        link = links.links[0]
                    else:
                        return None, "无法创建分享链接"
                else:
                    return None, str(e)
            
            # 转换为直接下载链接
            url = link.url.replace('?dl=0', '?dl=1')
            return url, None
            
        except Exception as e:
            return None, str(e)
    
    def upload_and_share(self, local_path, client_folder=""):
        """
        上传文件并创建分享链接
        返回: {'filename', 'dropbox_id', 'share_link', 'error'}
        """
        filename = os.path.basename(local_path)
        
        # 构建 Dropbox 路径
        if client_folder:
            dropbox_path = f"/客户文件交付/{client_folder}/{filename}"
        else:
            dropbox_path = f"/客户文件交付/{filename}"
        
        # 上传文件
        file_id, upload_error = self.upload_file(local_path, dropbox_path)
        if upload_error:
            return {
                'filename': filename,
                'dropbox_id': None,
                'share_link': None,
                'error': f"上传失败: {upload_error}"
            }
        
        # 创建分享链接
        share_url, share_error = self.create_share_link(dropbox_path)
        if share_error:
            return {
                'filename': filename,
                'dropbox_id': file_id,
                'share_link': None,
                'error': f"分享链接创建失败: {share_error}"
            }
        
        return {
            'filename': filename,
            'dropbox_id': file_id,
            'share_link': share_url,
            'error': None
        }
    
    def delete_file(self, dropbox_path):
        """删除 Dropbox 文件"""
        if not self.dbx:
            return False, "Dropbox 未认证"
        
        try:
            self.dbx.files_delete_v2(dropbox_path)
            return True, None
        except Exception as e:
            return False, str(e)


# 便捷函数
def upload_to_dropbox(file_path, client_folder=""):
    """上传文件到 Dropbox 并获取分享链接"""
    uploader = DropboxUploader()
    return uploader.upload_and_share(file_path, client_folder)


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"测试上传: {test_file}")
        result = upload_to_dropbox(test_file, "测试")
        print(f"结果: {result}")
    else:
        print("用法: python dropbox_uploader.py <文件路径>")

"""
Dropbox 上传模块 - 小豆豆文件传送系统
"""
import os
import dropbox
from dropbox.files import WriteMode
from dropbox.sharing import SharedLinkSettings, RequestedVisibility


def _is_shared_link_exists_error(error):
    """Handle Dropbox SDK union errors and older string-only errors."""
    sdk_error = getattr(error, "error", None)
    if sdk_error and hasattr(sdk_error, "is_shared_link_already_exists"):
        try:
            return sdk_error.is_shared_link_already_exists()
        except Exception:
            pass
    return "shared_link_already_exists" in str(error)


class DropboxUploader:
    def __init__(self, access_token=None):
        """初始化 Dropbox 上传器 - 支持 Refresh Token"""
        self.dbx = None

        # 首先尝试使用 Refresh Token（长期有效）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        refresh_token_path = os.path.join(script_dir, '..', 'config', 'dropbox_refresh_token.txt')
        credentials_path = os.path.join(script_dir, '..', 'config', 'dropbox_app_credentials.txt')

        if os.path.exists(refresh_token_path) and os.path.exists(credentials_path):
            try:
                with open(refresh_token_path, 'r') as f:
                    refresh_token = f.read().strip()
                with open(credentials_path, 'r') as f:
                    lines = f.read().strip().split('\n')
                    app_key = lines[0]
                    app_secret = lines[1]

                # 使用 Refresh Token 创建 Dropbox 客户端
                self.dbx = dropbox.Dropbox(
                    app_key=app_key,
                    app_secret=app_secret,
                    oauth2_refresh_token=refresh_token
                )
                return
            except Exception as e:
                print(f"⚠️ Refresh Token 方式失败: {e}")

        # 回退到旧的 Access Token 方式
        self.access_token = access_token or os.environ.get('DROPBOX_ACCESS_TOKEN')
        if not self.access_token:
            # 尝试从配置文件读取
            config_paths = [
                os.path.join(script_dir, '..', 'config', 'dropbox_token.txt'),
                '/Users/bear/.openclaw/workspace/file-delivery/config/dropbox_token.txt'
            ]
            for config_path in config_paths:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        self.access_token = f.read().strip()
                        break

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
                link = self.dbx.sharing_create_shared_link_with_settings(dropbox_path)
            except dropbox.exceptions.ApiError as e:
                # 如果链接已存在，获取现有链接
                if _is_shared_link_exists_error(e):
                    link = self.get_share_link_from_exists_error(e)
                    if not link:
                        link = self.get_existing_share_link(dropbox_path)
                    if not link:
                        return None, "分享链接已存在，但无法读取现有链接"
                else:
                    return None, str(e)

            # 转换为直接下载链接
            url = link.url.replace('?dl=0', '?dl=1')
            return url, None

        except Exception as e:
            return None, str(e)


    def get_share_link_from_exists_error(self, error):
        """Dropbox returns existing link metadata in shared_link_already_exists errors."""
        sdk_error = getattr(error, "error", None)
        if not sdk_error or not hasattr(sdk_error, "get_shared_link_already_exists"):
            return None

        try:
            existing = sdk_error.get_shared_link_already_exists()
            if hasattr(existing, "is_metadata") and existing.is_metadata():
                return existing.get_metadata()
        except Exception:
            return None

        return None

    def get_existing_share_link(self, dropbox_path):
        """读取 Dropbox 已有分享链接。"""
        if not self.dbx:
            return None

        try:
            links = self.dbx.sharing_list_shared_links(
                path=dropbox_path,
                direct_only=True
            )
            if links.links:
                return links.links[0]
        except Exception:
            pass

        try:
            links = self.dbx.sharing_list_shared_links(path=dropbox_path)
            if links.links:
                return links.links[0]
        except Exception:
            return None

        return None

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

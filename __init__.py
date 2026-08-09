# BookOasis 독서 업적 네이티브 플러그인 클래스를 외부에 노출합니다.
from .achievements import PLUGIN_VERSION, AchievementsMetadataProvider

__all__ = ["AchievementsMetadataProvider", "PLUGIN_VERSION"]

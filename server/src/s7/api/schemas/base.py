"""APIのスキーマの共通の基底クラス。"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """キー名をcamelCaseに変換する(Pythonの名前はsnake_case)。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

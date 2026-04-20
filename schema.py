from dataclasses import dataclass
from typing import Optional

@dataclass
class FeatureItem:
    module: str
    function_name: str
    level1: str
    level2: Optional[str]
    level3: Optional[str]
    level4: Optional[str]
    description: str
    importance: str
    url: str
"""将来の公式API・AI連携の境界。第1段階では外部通信しない。"""
from typing import Protocol

class ContentProvider(Protocol):
    def fetch(self, url: str) -> dict:
        """取得元、取得時刻、取得できない項目を含めて返す。"""
        ...

class AnalysisProvider(Protocol):
    def analyze(self, content: dict) -> list[dict]:
        """根拠・確認状態を持つ分析結果を返す。"""
        ...

class UnconfiguredProvider:
    def fetch(self, url: str) -> dict:
        raise NotImplementedError('API未接続です。URLからの自動取得は実装していません。')

    def analyze(self, content: dict) -> list[dict]:
        raise NotImplementedError('AI未接続です。外部への送信は行いません。')

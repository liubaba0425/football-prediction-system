#!/usr/bin/env python3
"""
赔率变化追踪器 — 记录同一场比赛赔率随时间的变化
用途: 检测赔率异动，辅助判断机构意图
"""
import os, json, csv
from datetime import datetime
from typing import Dict, List, Optional

class OddsTracker:
    """赔率追踪器 — 记录每次预测时的赔率快照"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = data_dir
        self.snapshots_path = os.path.join(data_dir, "odds_snapshots.json")
        self._ensure_file()
    
    def _ensure_file(self):
        if not os.path.exists(self.snapshots_path):
            with open(self.snapshots_path, 'w') as f:
                json.dump({}, f)
    
    def _load(self) -> Dict:
        with open(self.snapshots_path, 'r') as f:
            return json.load(f)
    
    def _save(self, data: Dict):
        with open(self.snapshots_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def record_snapshot(self, match_key: str, odds_data: Dict, 
                        prediction: Dict = None) -> str:
        """
        记录一次赔率快照
        
        Args:
            match_key: "主队_客队_日期" 唯一标识
            odds_data: {home_odds, draw_odds, away_odds, handicap, totals, ...}
            prediction: 可选，关联的预测结果
        
        Returns:
            snapshot_id
        """
        data = self._load()
        
        if match_key not in data:
            data[match_key] = {"snapshots": []}
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "odds": odds_data,
        }
        if prediction:
            snapshot["prediction"] = {
                "recommendation": prediction.get("recommendation", ""),
                "confidence": prediction.get("confidence", 0),
            }
        
        data[match_key]["snapshots"].append(snapshot)
        self._save(data)
        
        # Detect changes if multiple snapshots
        changes = self.detect_changes(match_key)
        if changes:
            data[match_key]["latest_changes"] = changes
            self._save(data)
        
        return snapshot["timestamp"]
    
    def detect_changes(self, match_key: str) -> List[Dict]:
        """检测赔率变化趋势"""
        data = self._load()
        match_data = data.get(match_key, {})
        snapshots = match_data.get("snapshots", [])
        
        if len(snapshots) < 2:
            return []
        
        first = snapshots[0]["odds"]
        latest = snapshots[-1]["odds"]
        changes = []
        
        # 胜平负赔率变化
        for key, label in [("home_odds", "主胜赔率"), 
                           ("draw_odds", "平局赔率"),
                           ("away_odds", "客胜赔率")]:
            if key in first and key in latest:
                old_v = first[key]
                new_v = latest[key]
                if abs(new_v - old_v) > 0.05:
                    direction = "↑" if new_v > old_v else "↓"
                    changes.append({
                        "field": label,
                        "from": round(old_v, 2),
                        "to": round(new_v, 2),
                        "direction": direction,
                        "change_pct": round((new_v - old_v) / old_v * 100, 1)
                    })
        
        # 盘口变化
        if "handicap" in first and "handicap" in latest:
            old_h = first["handicap"]
            new_h = latest["handicap"]
            if abs(new_h - old_h) > 0.01:
                changes.append({
                    "field": "让球盘口",
                    "from": old_h,
                    "to": new_h,
                    "direction": "↑" if new_h > old_h else "↓"
                })
        
        return changes
    
    def get_odds_movement(self, match_key: str) -> Optional[Dict]:
        """获取赔率异动摘要（用于预测报告）"""
        changes = self.detect_changes(match_key)
        if not changes:
            return None
        
        # 分析异动含义
        summary = {
            "has_movement": True,
            "changes": changes,
            "interpretation": self._interpret_movement(changes)
        }
        return summary
    
    def _interpret_movement(self, changes: List[Dict]) -> str:
        """解读赔率异动含义"""
        interpretations = []
        
        for c in changes:
            field = c["field"]
            direction = c["direction"]
            
            if field == "主胜赔率":
                if direction == "↓":
                    interpretations.append("机构降低主胜赔付，看好主队")
                else:
                    interpretations.append("机构升高主胜赔付，看淡主队")
            elif field == "客胜赔率":
                if direction == "↓":
                    interpretations.append("机构降低客胜赔付，看好客队")
                else:
                    interpretations.append("机构升高客胜赔付，看淡客队")
            elif field == "让球盘口":
                if direction == "↓":
                    interpretations.append("盘口下调，机构对让球方信心下降")
                else:
                    interpretations.append("盘口上调，机构对让球方信心增强")
        
        return "；".join(interpretations) if interpretations else "无明显异动"

# 全局单例
_tracker_instance = None

def get_odds_tracker() -> OddsTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = OddsTracker()
    return _tracker_instance

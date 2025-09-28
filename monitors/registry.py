from typing import Dict, Type, Callable

MONITOR_REGISTRY: Dict[str, Type] = {}


def register_monitor(name: str) -> Callable[[Type], Type]:
    """类装饰器：注册监控器到注册表。

    用法：
    @register_monitor("mokahr")
    class MokaHRMonitor(...):
        ...
    """

    def decorator(cls: Type) -> Type:
        key = name.strip().lower()
        MONITOR_REGISTRY[key] = cls
        return cls

    return decorator


def get_monitor_class(name: str):
    return MONITOR_REGISTRY.get((name or "").strip().lower())

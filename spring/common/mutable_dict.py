from typing import Generic, TypeVar, MutableMapping, Iterable, Tuple, List, Iterator

K = TypeVar('K')
V = TypeVar('V')


class MutableDict(MutableMapping[K, V], Generic[K, V]):
    def __init__(self, d: Iterable[Tuple[K, V]]):
        self._items: List[Tuple[K, V]] = list(d)

    def __getitem__(self, item: K) -> V:
        for key, value in self._items:
            if key == item:
                return value
        raise KeyError(item)

    def __setitem__(self, key: K, value: V):
        for i in range(len(self._items)):
            if self._items[i][0] == key:
                self._items[i] = key, value
                return
        self._items.append((key, value))
        # raise KeyError(key)

    def __delitem__(self, key: K):
        for i in range(len(self._items)):
            if self._items[i][0] == key:
                self._items.pop(i)
                return
        raise KeyError(key)

    def __len__(self):
        return len(self._items)

    def __iter__(self) -> Iterator[Tuple[K, V]]:
        for k, v in self._items:
            yield k

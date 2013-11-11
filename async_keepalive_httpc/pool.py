#!/usr/bin/env python
import logging


def _find_best_resource(res_list):
    for r in res_list:
        if len(r) == 0:
            return r, False

    return min(*res_list, key=len), True


class ResourcePool(object):

    def __init__(self, create_func, find_best_resource=None, init_count=0, max_count=4):
        self._pool = []
        self.init_count = init_count
        self.max_count = max_count
        self.create_func = create_func
        self.logger = logging.getLogger(ResourcePool.__name__)
        if find_best_resource:
            self.find_best_resource = find_best_resource
        else:
            self.find_best_resource = _find_best_resource

        for i in xrange(self.init_count):
            self._increase()

    def _increase(self):
        if len(self._pool) < self.max_count:
            ret = self.create_func()
            ret.res_id = len(self._pool)
            self._pool.append(ret)
            return ret
        return None

    def get(self):
        res, should_new = self.find_best_resource(self._pool)

        if should_new and len(self._pool) < self.max_count:
            return self._increase()

        return res

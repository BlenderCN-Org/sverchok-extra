
import numpy as np

from sverchok.utils.curve import SvCurve

##################
#                #
#  Curves        #
#                #
##################

class SvExGeomdlCurve(SvCurve):
    def __init__(self, curve):
        self.curve = curve
        self.u_bounds = (0.0, 1.0)

    def evaluate(self, t):
        v = self.curve.evaluate_single(t)
        return np.array(v)

    def evaluate_array(self, ts):
        t_min, t_max = self.get_u_bounds()
        ts[ts < t_min] = t_min
        ts[ts > t_max] = t_max
        vs = self.curve.evaluate_list(list(ts))
        return np.array(vs)

    def tangent(self, t):
        p, t = self.curve.tangent(t, normalize=False)
        return np.array(t)

    def tangent_array(self, ts):
        t_min, t_max = self.get_u_bounds()
        ts[ts < t_min] = t_min
        ts[ts > t_max] = t_max
        vs = self.curve.tangent(list(ts), normalize=False)
        return np.array([t[1] for t in vs])

    def second_derivative(self, t):
        p, first, second = self.curve.derivatives(t, order=2)
        return np.array(second)

    def second_derivative_array(self, ts):
        return np.vectorize(self.second_derivative, signature='()->(3)')(ts)

    def third_derivative(self, t):
        p, first, second, third = self.curve.derivatives(t, order=3)
        return np.array(third)

    def third_derivative_array(self, ts):
        return np.vectorize(self.third_derivative, signature='()->(3)')(ts)

    def derivatives_array(self, n, ts):
        def derivatives(t):
            result = self.curve.derivatives(t, order=n)
            return np.array(result[1:])
        result = np.vectorize(derivatives, signature='()->(n,3)')(ts)
        result = np.transpose(result, axes=(1, 0, 2))
        return result

    def get_u_bounds(self):
        return self.u_bounds

class SvExRbfCurve(SvCurve):
    def __init__(self, rbf, u_bounds):
        self.rbf = rbf
        self.u_bounds = u_bounds
        self.tangent_delta = 0.0001

    def get_u_bounds(self):
        return self.u_bounds

    def evaluate(self, t):
        v = self.rbf(t)
        return v

    def evaluate_array(self, ts):
        vs = self.rbf(ts)
        return vs

    def tangent(self, t):
        point = self.rbf(t)
        point_h = self.rbf(t+self.tangent_delta)
        return (point_h - point) / self.tangent_delta
    
    def tangent_array(self, ts):
        points = self.rbf(ts)
        points_h = self.rbf(ts+self.tangent_delta)
        return (points_h - points) / self.tangent_delta

def register():
    pass

def unregister():
    pass



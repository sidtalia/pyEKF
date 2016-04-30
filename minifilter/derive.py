import sys
sys.path.append('..')
from sympy import *
from helpers import *
import math

from symbols import *

P_symmetric = P
for r in range(P_symmetric.rows):
    for c in range(P_symmetric.cols):
        if r > c:
            P_symmetric[c,r] = P_symmetric[r,c]

def derivePrediction(jsonfile):
    errQuat = rot_vec_to_quat_approx(rotErr)
    truthQuat = quat_multiply(q, errQuat)
    Tbn = quat_to_matrix(truthQuat)
    deltaQuat = rot_vec_to_quat_approx(dAngMeas)
    truthQuatNew = quat_multiply(truthQuat, deltaQuat)
    errQuatNew = quat_multiply(quat_inverse(q), truthQuatNew)
    rotErrNew = quat_to_rot_vec_approx(errQuatNew)
    velNEDNew = velNED+gravityNED*dt+Tbn*dVelMeas

    # f: state transtition model
    f = toVec(rotErrNew, velNEDNew)

    # F: linearized state-transition model
    F = f.jacobian(x)

    # G: control-influence matrix, AKA "B" in literature
    G = f.jacobian(u)

    # covariance of additive noise on control inputs (u)
    Q_u = diag(*w_u.multiply_elementwise(w_u))

    # covariance of additive noise on states (x)
    Q = G*Q_u*G.T

    # x_n: state vector after prediction step
    x_n = f

    # P_n: covariance matrix after prediction step
    P_n = F*P*F.T + Q

    # q_n: reference quaternion after prediction step
    #q_n = q
    q_n = quat_normalize(quat_multiply(q, rot_vec_to_quat(x_n[0:3,0])))
    x_n[0:3,0] = (0.,0.,0.)

    # assume symmetry
    P_n = P_n.subs(zip(P, P_symmetric))

    x_n, P_n, q_n, subexp = extractSubexpressions([x_n,P_n,q_n],'subexp')

    saveExprsToJSON(jsonfile, {'Tbn': Tbn, 'x_n': x_n, 'P_n':P_n, 'q_n': q_n, 'subexp':subexp})

def deriveUpdate(jsonfile):
    # P_n: covariance matrix after update step
    P_n = P

    # x_n: state vector after update step
    x_n = x

    # h: predicted measurement
    h = velNED

    # y: measurement innovation
    y = velNEDMeas-h

    # sequential fusion
    for i in range(len(h)):
        # H: observation sensitivity matrix
        H = Matrix([[h[i]]]).jacobian(x)

        # K: near-optimal kalman gain
        K = (P*H.T)/(H*P*H.T + Matrix([[R_VEL]]))[0]

        x_n = x_n + K*y[i]

        P_n = (eye(nStates)-K*H)*P_n

    # q_n: reference quaternion after update step
    q_n = q

    x_n, P_n, q_n, subexp = extractSubexpressions([x_n,P_n,q_n],'subexp')

    saveExprsToJSON(jsonfile, {'x_n': x_n, 'P_n':P_n, 'q_n': q_n, 'subexp':subexp})

predictjson = 'minipredict.json'
updatejson = 'miniupdate.json'

derivePrediction(predictjson)
deriveUpdate(updatejson)

from PySide2 import QtWidgets, QtGui, QtCore
import math
import pymel.core as pm
import maya.cmds as cmds
import maya.OpenMayaUI as omui

import lib
try:    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    long
except NameError:   # Python 3 compatibility
    long = int
    unicode = str

Wgt_instance = None
j_num = 4

class DeformerSetter(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(DeformerSetter, self).__init__(parent)
        if not pm.ls(sl=1):
            pm.warning('Select geo first')
            return
        self.geo = pm.ls(sl=1)[0]
        self.curve = None
        self.joint_lst = None
        self.sel_obj = None
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle('Deform')
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.logger = lib.Logger(self.__class__.__name__ + cmds.ls(sl=1)[0])
        self.log = self.logger.load()
        if self.log:
            self.delete_all_btn.setVisible(True)
            self.lattice_wgt.setVisible(False)
        else:
            self.create_locators()

    def create_locators(self):
        self.loc_up = pm.spaceLocator(n='chain_loc_up')
        self.loc_up.ty.set(1)
        self.loc_down = pm.spaceLocator(n='chain_loc_down')
        pm.warning('Place 2 locators for spline, on top and bottom of deformable geo')
        pm.warning('Then press create lattice')
        pm.select(self.loc_up)



    def create_widgets(self):
        self.create_lattice_btn = QtWidgets.QPushButton('Create Lattice')
        self.lattice_lable = QtWidgets.QLabel('Lattice dimension')
        int_validator = QtGui.QIntValidator()
        self.x_dem = QtWidgets.QLineEdit('2')
        self.x_dem.setValidator(int_validator)
        self.y_dem = QtWidgets.QLineEdit('4')
        self.y_dem.setValidator(int_validator)
        self.z_dem = QtWidgets.QLineEdit('2')
        self.z_dem.setValidator(int_validator)

        self.delete_all_btn = QtWidgets.QPushButton('Delete')
        self.delete_all_btn.setVisible(False)


    def create_layouts(self):
        self.main_lo = QtWidgets.QHBoxLayout(self)

        self.lattice_lo = QtWidgets.QVBoxLayout(self)
        self.lattice_wgt = QtWidgets.QWidget()
        self.lattice_wgt.setLayout(self.lattice_lo)
        self.lattice_lo.addWidget(self.lattice_lable)
        self.lattice_lo.addWidget(self.x_dem)
        self.lattice_lo.addWidget(self.y_dem)
        self.lattice_lo.addWidget(self.z_dem)
        self.lattice_lo.addWidget(self.create_lattice_btn)

        self.main_lo.addWidget(self.lattice_wgt)

        self.main_lo.addWidget(self.delete_all_btn)

    def create_connections(self):
        self.create_lattice_btn.clicked.connect(self.create_lattice)
        self.delete_all_btn.clicked.connect(self.delete_all)


    def create_lattice(self):
        joint_lst = curveToJoints(self.logger,
                                       j_num,
                                       self.loc_up,
                                       self.loc_down)
        strch_off, strch_rig = set_ik_math(self.logger,
                    joint_lst)

        lattice, ffb = set_lattice(self.logger,
                    self.geo,
                    self.x_dem.text(),
                    self.y_dem.text(),
                    self.z_dem.text(),
                    joint_lst)
        root = self.logger.create_node('transform', n='stretch_deformer')
        elem_lst = [strch_off, strch_rig, lattice, ffb]
        pm.parent(elem_lst, root)
        self.logger.dump()
        #


    def delete_all(self):
        self.logger.undo()

def create_ui():
    global Wgt_instance
    if Wgt_instance is None:
        q_maya_window = get_maya_window()
        Wgt_instance = DeformerSetter(parent=q_maya_window)

    Wgt_instance.show()
    Wgt_instance.setWindowState(QtCore.Qt.WindowNoState | QtCore.Qt.WindowActive)
    Wgt_instance.activateWindow()
    return Wgt_instance

def get_maya_window():
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return wrp(long(ptr), QtWidgets.QMainWindow)

def set_lattice(logger, geo, x, y, z, jnt_lst):
    try:
        base, lattice, ffb = logger.lattice(geo, divisions=(int(x), int(y), int(z)), objectCentered=True)
        pm.skinCluster(jnt_lst, lattice, tsb=1)

        head_j = pm.ls('Head_M')
        if head_j:
            pm.parentConstraint(head_j, ffb, mo=1)
        return lattice, ffb
    except:
        pm.warning('So, nuclear homing missle launched at your coordinates')
        pm.warning('if serious, you messed up with lattice dimension fields or no object selected')
        return None


def curveToJoints(logger, j_num, loc_up, loc_down, direction=True):
    joint_lst = []
    curve = pm.curve(d=3, periodic=0, n='stretch_curva',
                     p=[pm.xform(loc_up, ws=1, q=1, t=1),
                        pm.xform(loc_up, ws=1, q=1, t=1),
                        pm.xform(loc_down, ws=1, q=1, t=1),
                        pm.xform(loc_down, ws=1, q=1, t=1)],
                     )
    shape = pm.listRelatives(curve, shapes=1)

    if pm.objectType(shape) == "nurbsCurve":
        newCV = pm.duplicate(shape, n="myRebuildCurve")
        rebuildCV = pm.rebuildCurve(
            newCV, rt=0, s=j_num, replaceOriginal=True)

        cmds.delete("{0}.cv[1]".format(rebuildCV[0]))
        cmds.delete("{1}.cv[{0}]".format(j_num, rebuildCV[0]))

        if direction:
            i = 1
            for x in range(0, j_num + 1)[::-1]:

                cvPoint = "{1}.cv[{0}]".format(x, rebuildCV[0])
                locPos = cmds.xform(cvPoint, q=True, ws=True, t=True)
                joint = logger.joint(
                    p=(locPos[0], locPos[1], locPos[2]), a=True, n=f'stretch_joint_{i}', roo='zxy')
                joint_lst.append(joint)
                i += 1
        else:
            i = 1
            for x in range(0, j_num + 1):

                cvPoint = "{1}.cv[{0}]".format(x, rebuildCV[0])
                locPos = cmds.xform(cvPoint, q=True, ws=True, t=True)
                joint = logger.joint(
                    p=(locPos[0], locPos[1], locPos[2]), a=True, n=f'stretch_joint_{i}', roo='zxy')
                joint_lst.append(joint)
                i += 1
        cmds.delete(rebuildCV)

    pm.delete(curve)
    pm.delete(loc_up)
    pm.delete(loc_down)

    return joint_lst



def  set_ik_math(logger, joint_lst):
    # create joint chain in geo

    str_offset = logger.create_node('transform', n='stretch_control')
    str_main = logger.create_node('transform', n='stretch_rig')
    str_skeleton = logger.create_node('transform', n='stretch_skeleton')
    head_j = pm.ls('Head_M')
    if head_j:
        coord = pm.xform(head_j[0], ws=1, q=1, t=1)
        pm.xform(str_offset, t=coord)
        pm.xform(str_skeleton, t=coord)

    pos1 = pm.xform(joint_lst[0], ws=1, q=1, t=1)
    pos2 = pm.xform(joint_lst[-1], ws=1, q=1, t=1)

    loc1 = logger.space_locator(n='stretch_control', p=pm.xform(joint_lst[0], ws=1, q=1, t=1))
    pm.xform(loc1, cpc=1)
    loc2 = logger.space_locator(n='stretch_cv_2', p=pm.xform(joint_lst[math.floor(len(joint_lst) / 2)], ws=1, q=1, t=1))
    loc3 = logger.space_locator(n='stretch_cv_3', p=pm.xform(joint_lst[math.floor(len(joint_lst) / 2)], ws=1, q=1, t=1))
    loc4 = logger.space_locator(n='stretch_cv_4', p=pm.xform(joint_lst[-1], ws=1, q=1, t=1))

    curve = logger.curve(n='stretch_curve', d=3, periodic=0, p=[(pos1[0], pos1[1], pos1[2]),
                                                            (pos1[0], pos1[1], pos1[2]),
                                                            (pos2[0], pos2[1], pos2[2]),
                                                            (pos2[0], pos2[1], pos2[2])])

    # control1 = logger.circle(n='Stretch_control_1', c=[pos1[0], pos1[1], pos1[2]], nr=[0,1,0])
    control1 = logger.curve(d=1, p=[(0, 1, 0), (-0.382683, 0.92388, 0), (-0.707107, 0.707107, 0), (-0.92388, 0.382683, 0), (-1, 0, 0), (-0.92388, -0.382683, 0), (-0.707107, -0.707107, 0), (-0.382683, -0.92388, 0), (0, -1, 0), (0.382683, -0.92388, 0), (0.707107, -0.707107, 0), (0.92388, -0.382683, 0), (1, 0, 0), (0.92388, 0.382683, 0), (0.707107, 0.707107, 0), (0.382683, 0.92388, 0), (0, 1, 0), (0, 0.92388, 0.382683), (0, 0.707107, 0.707107), (0, 0.382683, 0.92388), (0, 0, 1), (0, -0.382683, 0.92388), (0, -0.707107, 0.707107), (0, -0.92388, 0.382683), (0, -1, 0), (0, -0.92388, -0.382683), (0, -0.707107, -0.707107), (0, -0.382683, -0.92388), (0, 0, -1), (0, 0.382683, -0.92388), (0, 0.707107, -0.707107), (0, 0.92388, -0.382683), (0, 1, 0), (-0.382683, 0.92388, 0), (-0.707107, 0.707107, 0), (-0.92388, 0.382683, 0), (-1, 0, 0), (-0.92388, 0, 0.382683), (-0.707107, 0, 0.707107), (-0.382683, 0, 0.92388), (0, 0, 1), (0.382683, 0, 0.92388), (0.707107, 0, 0.707107), (0.92388, 0, 0.382683), (1, 0, 0), (0.92388, 0, -0.382683), (0.707107, 0, -0.707107), (0.382683, 0, -0.92388), (0, 0, -1), (-0.382683, 0, -0.92388), (-0.707107, 0, -0.707107), (-0.92388, 0, -0.382683), (-1, 0, 0)], k=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52], n='Stretch_control_1')
    pm.xform(control1, cpc=1)
    pm.xform(control1, t=pos1)
    control2 = logger.curve(d=1, p=[(0, 1, 0), (-0.382683, 0.92388, 0), (-0.707107, 0.707107, 0), (-0.92388, 0.382683, 0), (-1, 0, 0), (-0.92388, -0.382683, 0), (-0.707107, -0.707107, 0), (-0.382683, -0.92388, 0), (0, -1, 0), (0.382683, -0.92388, 0), (0.707107, -0.707107, 0), (0.92388, -0.382683, 0), (1, 0, 0), (0.92388, 0.382683, 0), (0.707107, 0.707107, 0), (0.382683, 0.92388, 0), (0, 1, 0), (0, 0.92388, 0.382683), (0, 0.707107, 0.707107), (0, 0.382683, 0.92388), (0, 0, 1), (0, -0.382683, 0.92388), (0, -0.707107, 0.707107), (0, -0.92388, 0.382683), (0, -1, 0), (0, -0.92388, -0.382683), (0, -0.707107, -0.707107), (0, -0.382683, -0.92388), (0, 0, -1), (0, 0.382683, -0.92388), (0, 0.707107, -0.707107), (0, 0.92388, -0.382683), (0, 1, 0), (-0.382683, 0.92388, 0), (-0.707107, 0.707107, 0), (-0.92388, 0.382683, 0), (-1, 0, 0), (-0.92388, 0, 0.382683), (-0.707107, 0, 0.707107), (-0.382683, 0, 0.92388), (0, 0, 1), (0.382683, 0, 0.92388), (0.707107, 0, 0.707107), (0.92388, 0, 0.382683), (1, 0, 0), (0.92388, 0, -0.382683), (0.707107, 0, -0.707107), (0.382683, 0, -0.92388), (0, 0, -1), (-0.382683, 0, -0.92388), (-0.707107, 0, -0.707107), (-0.92388, 0, -0.382683), (-1, 0, 0)], k=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52], n='Stretch_control_2')
    pm.xform(control2, cpc=1)
    pm.xform(control2, t=pos2)

    loc_lst = [loc1, loc2, loc3, loc4]

    for loc in loc_lst:
        loc.visibility.set(0)
    pm.parent(loc_lst, str_offset)
    pm.parent(joint_lst[0], str_skeleton)
    pm.parent(str_skeleton, str_main)
    pm.parent(control1, str_offset)
    pm.parent(control2, str_offset)
    pm.parent(str_offset, str_main)
    ik_handle, effector = logger.ik_handle(sj=joint_lst[0], ee=joint_lst[-1], solver='ikSplineSolver', ccv=0, c=curve,
                                      n='ikHandle_stretch')
    ik_handle.visibility.set(0)
    pm.parent(ik_handle, str_skeleton)

    for x in [str_skeleton, str_offset, control1, control2]:
        cmds.makeIdentity(x.name(), apply=1, t=1, r=1, s=1, n=0, pn=1)

    pm.parentConstraint(control1, loc1, mo=1)
    pm.parentConstraint(control2, loc4, mo=1)
    pm.parentConstraint(head_j, str_skeleton, mo=1)
    pm.parentConstraint(head_j, str_offset, mo=1)

    for i, l in enumerate(loc_lst):
        l.worldPosition[0] >> curve.controlPoints[i]

    info = logger.create_node('curveInfo')

    curve.worldSpace[0] >> info.inputCurve

    math1 = logger.create_node('floatMath')
    math1.operation.set(3)
    math1.floatB.set(info.arcLength.get())

    math2 = logger.create_node('floatMath')
    math2.floatB.set(0.5)
    math2.operation.set(6)

    math3 = logger.create_node('floatMath')
    math3.operation.set(3)
    math3.floatA.set(1)

    info.arcLength >> math1.floatA

    math1.outFloat >> math2.floatA

    math2.outFloat >> math3.floatB

    for j in joint_lst:
        math1.outFloat >> j.scaleY
        math3.outFloat >> j.scaleX
        math3.outFloat >> j.scaleZ
    pm.parent(curve, w=1)
    pm.parent(curve, str_main)


    return str_offset, str_main


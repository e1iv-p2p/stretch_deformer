import pymel.core as pm
import json
from maya import cmds

class Logger(object):
    def __init__(self, module_name):
        self.log = {"nodes": [], "connections": [], "disconnections": [], "attrs": [], 
        "parents": [], "groups": [], "locked_state": [], "k_state": [], "cb_state":[], "constraint_targets": [], "attr_vals": []}
        self.conf_node_name = module_name

    def create_node(self, *args, **kwargs):
        node = pm.createNode(*args, **kwargs)
        self.log["nodes"].append(node.name())
        return node

    def curve(self, *args, **kwargs):
        node = pm.curve(*args, **kwargs)
        self.log["nodes"].append(node.name())
        return node

    def circle(self, *args, **kwargs):
        node = pm.circle(*args, **kwargs)[0]
        self.log["nodes"].append(node.name())
        return node

    def space_locator(self, *args, **kwargs):
        node = pm.spaceLocator(*args, **kwargs)
        self.log["nodes"].append(node.name())
        return node

    def joint(self, *args, **kwargs):
        node = pm.joint(*args, **kwargs)
        self.log["nodes"].append(node.name())
        return node

    def parent_constraint(self, *args, **kwargs):
        source = pm.PyNode(args[-1])
        lst = list(set(source.inputs(type="parentConstraint")))
        if lst:
            ex_constraint = lst[0]
            old_targets = ex_constraint.getTargetList()
            node = pm.parentConstraint(*args, **kwargs)
            self.log["constraint_targets"].append({"source": source.name(), "old_targets": [x.name() for x in old_targets], "type": "parent", "constraint": ex_constraint.name()})
        else:
            node = pm.parentConstraint(*args, **kwargs)
            self.log["nodes"].append(node.name())
        return node

    def orient_constraint(self, *args, **kwargs):
        source = pm.PyNode(args[-1])
        lst = list(set(source.inputs(type="orientConstraint")))
        if lst:
            ex_constraint = lst[0]
            old_targets = ex_constraint.getTargetList()
            node = pm.orientConstraint(*args, **kwargs)
            self.log["constraint_targets"].append({"source": source.name(), "old_targets": [x.name() for x in old_targets], "type": "orient", "constraint": ex_constraint.name()})
        else:
            node = pm.orientConstraint(*args, **kwargs)
            self.log["nodes"].append(node.name())
        return node

    def point_constraint(self, *args, **kwargs):
        source = pm.PyNode(args[-1])
        lst = list(set(source.inputs(type="pointConstraint")))
        if lst:
            ex_constraint = lst[0]
            old_targets = ex_constraint.getTargetList()
            node = pm.pointConstraint(*args, **kwargs)
            self.log["constraint_targets"].append({"source": source.name(), "old_targets": [x.name() for x in old_targets], "type": "point", "constraint": ex_constraint.name()})
        else:
            node = pm.pointConstraint(*args, **kwargs)
            self.log["nodes"].append(node.name())
        return node

    def connect_attr(self, *args, **kwargs):
        old_value = None
        temp_value = pm.getAttr(args[1])
        if temp_value:
            if isinstance(temp_value, (int, bool, str, float)):
                old_value = temp_value

        dest_attr = pm.PyNode(args[1])
        if dest_attr.inputs():
            source_attr = dest_attr.inputs(p=True)[0]
            self.log["disconnections"].append({"from": source_attr.name(), "to": dest_attr.name()})

        pm.connectAttr(*args, **kwargs)
        self.log["connections"].append({"from": pm.PyNode(args[0]).name(), "to": pm.PyNode(args[1]).name(), "old_value": old_value})

    def disconnect_attr(self, *args, **kwargs):
        self.log["disconnections"].append({"from": pm.PyNode(args[0]).name(), "to": pm.PyNode(args[1]).name()})
        pm.disconnectAttr(*args, **kwargs)

    def create_attr(self, *args, **kwargs):
        node = pm.PyNode(args[0])
        pm.addAttr(*args, **kwargs)
        self.log["attrs"].append({"node": node.name(), "attr": kwargs["ln"]})

    def duplicate(self, *args, **kwargs):
        res = pm.duplicate(*args, **kwargs)
        for x in res:
            self.log["nodes"].append(x.name())
        return res

    def ik_handle(self, *args, **kwargs):
        res = pm.ikHandle(*args, **kwargs)
        for x in res:
            self.log["nodes"].append(x.name())
        return res

    def lattice(self, *args, **kwargs):
        res = pm.lattice(*args, **kwargs)
        for x in res:
            self.log["nodes"].append(x.name())
        return res

    def parent(self, a, b):
        node = pm.PyNode(a)
        parent = node.getParent()
        parent_name = None
        if parent:
            parent_name = parent.name()

        t = list(a.t.get())
        r = list(a.r.get())
        s = list(a.s.get())

        self.log["parents"].append({"node": node.name(), "parent": parent_name, "trs": [t, r, s]})
        res = pm.parent(a, b)
        return res

    def lock_attr(self, attr):
        pm.setAttr(attr, lock=True)
        self.log["locked_state"].append({"attr": attr.name(), "base_state": False})

    def unlock_attr(self, attr):
        pm.setAttr(attr, lock=True)
        self.log["locked_state"].append({"attr": attr.name(), "base_state": True})

    def hide_attr(self, attr):
        pm.setAttr(attr, k=False, cb=False)
        self.log["k_state"].append({"attr": attr.name(), "base_state": True})
        self.log["cb_state"].append({"attr": attr.name(), "base_state": True})

    def show_attr(self, attr):
        pm.setAttr(attr, k=True, cb=True)
        self.log["k_state"].append({"attr": attr.name(), "base_state": False})
        self.log["cb_state"].append({"attr": attr.name(), "base_state": False})

    def set_attr(self, *args, **kwargs):
        attr = pm.PyNode(args[0])
        val = attr.get()
        if isinstance(val, pm.dt.Vector):
            val = list(val)
        self.log["attr_vals"].append({"attr": attr.name(), "val": val})
        pm.setAttr(*args, **kwargs)

    def group(self, *args, **kwargs):
        temp_dic = {"transform": "", "parents":[]}
        for arg in args:
            old_parent = arg.getParent()
            if old_parent:
                old_parent = old_parent.name()
            temp_dic["parents"].append({"node": arg.name(), "parent": old_parent})

        res = pm.group(*args, **kwargs)
        temp_dic["transform"] = res.name()
        self.log["groups"].append(temp_dic)
        return res

    def dump(self):
        node = pm.ls("logger")
        if node:
            node = node[0]
        else:
            node = pm.createNode("network", n="logger")

        if not pm.attributeQuery(self.conf_node_name, n=node, ex=True):
            node.addAttr(self.conf_node_name, dt="string")

        node.attr(self.conf_node_name).set(json.dumps(self.log))

    def load(self):
        lst = pm.ls("logger." + self.conf_node_name)
        if not lst:
            return False
        str_val = lst[0].get()
        self.log = json.loads(str_val)
        return True

    def undo(self):
        for x in reversed(self.log["connections"]):
            if pm.objExists(x["from"]) and pm.objExists(x["to"]) and pm.isConnected(x["from"], x["to"]):
                pm.disconnectAttr(x["from"], x["to"])
                if x["old_value"]:
                    pm.setAttr(x["to"], x["old_value"])

        for x in reversed(self.log["constraint_targets"]):
            if not pm.objExists(x["source"]) or not pm.objExists(x["constraint"]):
                continue
            for target in pm.PyNode(x["constraint"]).getTargetList():
                if target.name() not in x["old_targets"]:
                    if x["type"] == "parent":
                        pm.parentConstraint(target, x["source"], e=True, rm=True)
                    elif x["type"] == "point":
                        pm.pointConstraint(target, x["source"], e=True, rm=True)
                    elif x["type"] == "orient":
                        pm.orientConstraint(target, x["source"], e=True, rm=True)
                    else:
                        continue

        for x in reversed(self.log["locked_state"]):
            if pm.objExists(x["attr"]):
                pm.setAttr(x["attr"], lock=x["base_state"])
        for x in reversed(self.log["k_state"]):
            if pm.objExists(x["attr"]):
                pm.setAttr(x["attr"], k=x["base_state"])
        for x in reversed(self.log["cb_state"]):
            if pm.objExists(x["attr"]):
                pm.setAttr(x["attr"], cb=x["base_state"])
        for x in reversed(self.log["attr_vals"]):
            if pm.objExists(x["attr"]):
                pm.setAttr(x["attr"], x["val"])
        for x in reversed(self.log["attrs"]):
            if pm.objExists(x["node"]) and pm.attributeQuery(x["attr"], node=x["node"], ex=True):
                pm.deleteAttr(x["node"], at=x["attr"])
        for x in reversed(self.log["parents"]):
            if pm.objExists(x["node"]):
                pm.parent(x["node"], x["parent"])
                for i, attr in enumerate([".t", ".r", ".s"]):
                    try:
                        pm.setAttr(x["node"] + attr, x["trs"][i])
                    except: pass

        for x in reversed(self.log["groups"]):
            for z in x["parents"]:
                if pm.objExists(z["node"]) and pm.objExists(z["parent"]):
                    pm.parent(z["node"], z["parent"])
            if pm.objExists(x["transform"]):
                pm.disconnectAttr(x["transform"])
                pm.delete(x["transform"])
        for x in reversed(self.log["nodes"]):
            if pm.objExists(x):
                pm.disconnectAttr(x)
                pm.delete(x)
        for x in reversed(self.log["disconnections"]):
            pm.connectAttr(x["from"], x["to"], f=True)
            # if x["old_value"]:
            #     pm.setAttr(x["to"], x["old_value"])
        pm.deleteAttr("logger." + self.conf_node_name)

def get_set_recursive(object_set):
    controls = []
    if not cmds.objExists(object_set):
        return controls
    subsets = cmds.listConnections(object_set, s=True, d=False, type="objectSet") or []
    for x in subsets:
        subset_controls = get_set_recursive(x)
        controls.extend(subset_controls)
    self_controls = cmds.listConnections(object_set, s=True, d=False, type="transform") or []
    controls.extend(self_controls)
    return controls
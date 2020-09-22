from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
#进行页面布局设置，因为有很多小器件#
class DyTreeWidget(QTreeWidget):
    """description of class"""
    # 初始化目录树结构，为了显示
    def __init__(self, fields, parent=None):
        """
        @fields foramt:
        @fields = [
                    ["level_0_a",
                        [
                            "level_1_a",
                                ["level_2_a", "leaf_id"(optional)],
                                ["level_2_b"]
                        ],
                        ["level_1_b"]
                    ],

                    ["level_0_b",
                        ["level_1_a"],
                        ["level_1_b"]
                    ]
                  ]

        For each leaf, e.g. "level_2" means show name. "leaf_id" means its unique ID in whole @fields, which is optional.
        If "leaf_id" isn't assigned, it will be generated like "level_0_a->level_1_a->1evel_2_a".
        So in same level, show name should be different.
        """
        super().__init__(parent)

        self._fields = fields
        self._leafIdMap = {} # {"leaf_id":tree widget item}, for restore tree item state from config file


        self.__InitFields(self, self._fields)# 递归初始化叶子节点，并且实例化对应的目录
        self.setHeaderHidden(True)

        self.expandAll()# 展开全部

        self.itemClicked.connect(self.on_itemClicked)# 点击项目
        self.itemChanged.connect(self.on_itemChanged)# 项目改变
        self.currentItemChanged.connect(self.on_currentItemChanged)# 现在的item改变

    def __GetFieldByShowName(self, fields, name):
        for field in fields:
            if isinstance(field, str):
                if name == field:
                    return fields[1]
            else: # list
                ret =  self.__GetFieldByShowName(field, name)
                if ret != None:
                    return ret

        return None

    def set(self, leafIds):
        """ set leaf's state checked
            @leafIds: []
        """

        for leafId in leafIds:
            if leafId in self._leafIdMap:
                self.__UpdateParent(self._leafIdMap[leafId])

    def __GetFields(self, parent):
        fields = []
        for i in range(parent.childCount()):
            childItem = parent.child(i)

            # leaf
            if childItem.childCount() == 0:
                if childItem.checkState(0) == Qt.Checked:
                    field = self.__GetFieldByShowName(self._fields, childItem.text(0))
                    fields.append(field)
                continue
            
            if childItem.checkState(0) == Qt.Checked or childItem.checkState(0) == Qt.PartiallyChecked:
                field = self.__GetFields(childItem)
                fields.extend(field)

        return fields

    # 实例化每一个item
    def __InitFieldItem(self, parent, item):
        treeItem = QTreeWidgetItem(parent)# 实例化ITEM
        treeItem.setText(0, item)
        treeItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        treeItem.setCheckState(0, Qt.Unchecked)

        return treeItem
    # 获得叶子节点
    def _getLeafId(self, leaf):
        leafId = None
        while leaf is not self and leaf is not None:
            leafId = leaf.text(0) if leafId is None  else leaf.text(0) + "->" + leafId

            leaf = leaf.parent()

        return leafId
    # 初始化域（递归）
    def __InitFields(self, parent, fields):
        for i, field in enumerate(fields):# 一层一层拨开，只要执行这个，外面少一个[],遍历里面的具体项目
            if isinstance(field, str):# 如CTA，必须是到字符串才能实例化
                if i == 0:# 那就是CTA这样的父目录，然后在递归，相对父亲，但不是叶子节点
                    parent = self.__InitFieldItem(parent, field)# 开始初始化这个field
                else: # leaf ID specified by user
                    self._leafIdMap[field] = parent# 添加映射
            else:
                self.__InitFields(parent, field)# 回归

        if i == 0: # dafault leaf ID
            leafId = self._getLeafId(parent)
            if leafId is not None:
                self._leafIdMap[leafId] = parent# 具体运行或者监控的那个实例

    def __UpdateChild(self, parent):
        for i in range(parent.childCount()):# 这个树枝下面还有没有树叶
            child = parent.child(i)
            child.setCheckState(0, parent.checkState(0))# 更具父的状态来更新子的状态

            self.__UpdateChild(child)# 递归

    #
    def __UpdateParent(self, child):
        parent = child.parent()
        if parent is None or parent is self: return


        partiallySelected = False
        selectedCount = 0
        childCount = parent.childCount()
        for i in range(childCount):
             childItem = parent.child(i)
             if childItem.checkState(0) == Qt.Checked:
                 selectedCount += 1
             elif childItem.checkState(0) == Qt.PartiallyChecked:
                 partiallySelected = True

        if partiallySelected:
            parent.setCheckState(0, Qt.PartiallyChecked)
        else:
            if selectedCount == 0:
                parent.setCheckState(0, Qt.Unchecked)
            elif selectedCount > 0 and selectedCount < childCount:
                parent.setCheckState(0, Qt.PartiallyChecked)
            else:
                parent.setCheckState(0, Qt.Checked)

        self.__UpdateParent(parent)
        '''
        复选框一共有三种状态：全选中、半选中和无选中。
        若一个父选项的子选项全部为选中状态，则该父选项为全选中；
        若子选项全部为无选中状态，则该父选项为无选中状态；
        若子选项既有全选中和无选中状态，则该父选项为半选中状态
        '''

    def __GetFieldsFromTreeWidget(self):
        fields = self.__GetFields(self.treeWidgetFields.invisibleRootItem())

        return fields


    def __SetFieldsIntoTreeWidget(self, fields):
        if fields:
            self.__SetFields(self.treeWidgetFields.invisibleRootItem(), fields)
    
    def on_itemClicked(self, item, column):
        pass
    # 子类继承实现
    def on_currentItemChanged(self, current, previous):
        pass
    #
    def on_itemChanged(self, item, column):
        self.blockSignals(True)
        # 先阻断信号，更新子目录，然后更新父目录, 更新按钮状态的
        self.__UpdateChild(item)
        self.__UpdateParent(item)
        # 之后不阻断状态
        self.blockSignals(False)

    def getCheckedTexts(self):

        texts = []
        for _, item in self._leafIdMap.items():
            if item.checkState(0) == Qt.Checked:
                texts.append(item.text(0))

        return texts

    def collapse(self, text):
        items = self.findItems(text, Qt.MatchExactly)
        for item in items:
            self.collapseItem(item)


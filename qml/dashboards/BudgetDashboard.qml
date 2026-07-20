import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts

Item {
    id: dashboard
    property int editingIncomeId: -1
    property int editingAllocationId: -1
    property int editingMonthlyItemId: -1
    readonly property int monthlyAmountColumnWidth: 135
    readonly property int monthlyActionsColumnWidth: 154

    function plainMoney(value) {
        return value.replace(/[$,]/g, "")
    }

    function editIncome(item) {
        editingIncomeId = item.id
        incomeName.text = item.name
        incomeType.currentIndex = Math.max(0, incomeType.find(item.income_type))
        annualIncome.text = plainMoney(item.annual)
        incomeName.forceActiveFocus()
    }

    function cancelIncomeEdit() {
        editingIncomeId = -1
        incomeName.clear()
        annualIncome.clear()
    }

    function editAllocation(item) {
        editingAllocationId = item.id
        allocationName.text = item.name
        allocationGroup.currentIndex = Math.max(0, allocationGroup.find(item.allocation_group))
        allocationAmount.text = plainMoney(item.monthly)
        allocationName.forceActiveFocus()
    }

    function cancelAllocationEdit() {
        editingAllocationId = -1
        allocationName.clear()
        allocationAmount.clear()
    }

    function editMonthlyItem(item) {
        editingMonthlyItemId = item.id
        budgetName.text = item.name
        budgetType.currentIndex = Math.max(0, budgetType.find(item.item_type))
        plannedAmount.text = plainMoney(item.planned)
        actualAmount.text = plainMoney(item.actual)
        budgetNotes.text = item.notes
        budgetName.forceActiveFocus()
    }

    function cancelMonthlyEdit() {
        editingMonthlyItemId = -1
        budgetName.clear()
        plannedAmount.clear()
        actualAmount.clear()
        budgetNotes.clear()
    }

    function changeBudgetMonth(offset) {
        cancelMonthlyEdit()
        budgetController.changeMonth(offset)
    }

    ColumnLayout {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 24
        anchors.bottomMargin: 24
        width: Math.min(parent.width - 48, 1120)
        spacing: 14

        ColumnLayout {
            spacing: 3
            Label {
                text: "Family budget"
                font.pixelSize: 27
                font.bold: true
                color: "#f4fbff"
            }
            Label {
                text: "Plan income, paycheck allocations, monthly spending, and savings in one place."
                font.pixelSize: 14
                color: "#91adbf"
            }
        }

        Rectangle {
            Layout.preferredWidth: 500
            Layout.preferredHeight: 44
            radius: 10
            color: "#0a1d33"
            border.color: "#17466a"

            Row {
                anchors.fill: parent
                anchors.margins: 4
                spacing: 4

                Button {
                    width: (parent.width - parent.spacing) / 2
                    height: parent.height
                    text: "Income && allocation"
                    flat: true
                    highlighted: budgetPages.currentIndex === 0
                    onClicked: budgetPages.currentIndex = 0
                }
                Button {
                    width: (parent.width - parent.spacing) / 2
                    height: parent.height
                    text: "Monthly spending && saving"
                    flat: true
                    highlighted: budgetPages.currentIndex === 1
                    onClicked: budgetPages.currentIndex = 1
                }
            }
        }

        StackLayout {
            id: budgetPages
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: 0

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Repeater {
                            model: [
                                { label: "MONTHLY GROSS", value: budgetController.monthlyGross, color: "#f4fbff" },
                                { label: "ALLOCATIONS", value: budgetController.monthlyAllocations, color: "#ffb454" },
                                { label: "ESTIMATED NET", value: budgetController.monthlyNet, color: "#55e879" }
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                height: 92
                                radius: 12
                                color: "#0a1d33"
                                border.color: "#17466a"
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 7
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: "#91adbf"; font.pixelSize: 11 }
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: modelData.color; font.pixelSize: 23; font.bold: true }
                                }
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "2026 planning assumptions: married filing jointly, one household income, standard deductions, two Virginia personal exemptions, no tax credits, and medical/dental premiums treated as pre-tax. Replace estimates with paystub amounts when available."
                        color: "#91adbf"
                        wrapMode: Text.WordWrap
                        font.pixelSize: 11
                    }

                    Label { text: dashboard.editingIncomeId < 0 ? "Add income source" : "Edit income source"; color: "#f4fbff"; font.bold: true; font.pixelSize: 16 }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: incomeName; Layout.fillWidth: true; placeholderText: "Income source" }
                        ComboBox { id: incomeType; model: ["Salary", "Hourly", "Bonus", "Other"] }
                        TextField { id: annualIncome; Layout.preferredWidth: 150; placeholderText: "Annual amount"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                        Button {
                            text: dashboard.editingIncomeId < 0 ? "Add income" : "Save changes"
                            highlighted: true
                            onClicked: {
                                var saved = dashboard.editingIncomeId < 0
                                          ? budgetController.saveIncomeSource(incomeName.text, incomeType.currentText, annualIncome.text)
                                          : budgetController.updateIncomeSource(dashboard.editingIncomeId, incomeName.text, incomeType.currentText, annualIncome.text)
                                if (saved)
                                    dashboard.cancelIncomeEdit()
                            }
                        }
                        Button { text: "Cancel"; visible: dashboard.editingIncomeId >= 0; onClicked: dashboard.cancelIncomeEdit() }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(contentHeight, 125)
                        clip: true
                        spacing: 4
                        model: budgetController.incomeSources
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width; height: 42; radius: 6; color: "#0c213a"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 7
                                Label { Layout.fillWidth: true; text: modelData.name + "  •  " + modelData.income_type }
                                Label { text: modelData.annual + " yearly  •  " + modelData.monthly + " monthly"; color: "#91adbf" }
                                Button { text: "Edit"; onClicked: dashboard.editIncome(modelData) }
                                Button { text: "Remove"; onClicked: budgetController.deleteIncomeSource(modelData.id) }
                            }
                        }
                    }

                    Label { text: dashboard.editingAllocationId < 0 ? "Add monthly payroll allocation" : "Edit monthly payroll allocation"; color: "#f4fbff"; font.bold: true; font.pixelSize: 16 }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: allocationName; Layout.fillWidth: true; placeholderText: "Tax, benefit, retirement…" }
                        ComboBox { id: allocationGroup; model: ["Tax", "Benefit", "Retirement", "Other"] }
                        TextField { id: allocationAmount; Layout.preferredWidth: 150; placeholderText: "Monthly amount"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                        Button {
                            text: dashboard.editingAllocationId < 0 ? "Add allocation" : "Save changes"
                            highlighted: true
                            onClicked: {
                                var saved = dashboard.editingAllocationId < 0
                                          ? budgetController.saveAllocation(allocationName.text, allocationGroup.currentText, allocationAmount.text)
                                          : budgetController.updateAllocation(dashboard.editingAllocationId, allocationName.text, allocationGroup.currentText, allocationAmount.text)
                                if (saved)
                                    dashboard.cancelAllocationEdit()
                            }
                        }
                        Button { text: "Cancel"; visible: dashboard.editingAllocationId >= 0; onClicked: dashboard.cancelAllocationEdit() }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: budgetController.allocations
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width; height: 42; radius: 6; color: "#0c213a"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 7
                                Label { Layout.fillWidth: true; text: modelData.name + "  •  " + modelData.allocation_group }
                                Label { text: modelData.monthly; color: "#ffb454"; font.bold: true }
                                Button { text: "Edit"; onClicked: dashboard.editAllocation(modelData) }
                                Button { text: "Remove"; onClicked: budgetController.deleteAllocation(modelData.id) }
                            }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 380
                        Layout.preferredHeight: 46
                        radius: 10
                        color: "#0a1d33"
                        border.color: "#17466a"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 4
                            ToolButton {
                                text: "‹"
                                font.pixelSize: 22
                                Accessible.name: "Previous month"
                                onClicked: dashboard.changeBudgetMonth(-1)
                            }
                            Label {
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                                text: budgetController.currentMonthLabel
                                font.pixelSize: 19
                                font.bold: true
                                color: "#55dff4"
                            }
                            ToolButton {
                                text: "›"
                                font.pixelSize: 22
                                Accessible.name: "Next month"
                                onClicked: dashboard.changeBudgetMonth(1)
                            }
                        }
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 5
                        Repeater {
                            model: [
                                { label: "NET INCOME", value: budgetController.monthlyNet, color: "#f4fbff" },
                                { label: "PLANNED SPENDING", value: budgetController.plannedSpending, color: "#ffb454" },
                                { label: "PLANNED SAVING", value: budgetController.plannedSaving, color: "#55dff4" },
                                { label: "REMAINING", value: budgetController.plannedRemaining, color: budgetController.plannedRemaining.charAt(0) === "-" ? "#ff647c" : "#55e879" },
                                { label: "ACTUAL REMAINING", value: budgetController.actualRemaining, color: budgetController.actualRemaining.charAt(0) === "-" ? "#ff647c" : "#55e879" }
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; height: 84; radius: 11; color: "#0a1d33"; border.color: "#17466a"
                                Column { anchors.centerIn: parent; spacing: 4
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: "#91adbf"; font.pixelSize: 10 }
                                    Label { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: modelData.color; font.pixelSize: 16; font.bold: true }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 138
                        radius: 12
                        color: "#0a1d33"
                        border.color: "#17466a"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8

                            Label {
                                text: dashboard.editingMonthlyItemId < 0
                                      ? "Add a monthly category"
                                      : "Edit monthly category"
                                color: "#f4fbff"
                                font.bold: true
                                font.pixelSize: 16
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: 5
                                columnSpacing: 8
                                TextField { id: budgetName; Layout.fillWidth: true; placeholderText: "Category name" }
                                ComboBox { id: budgetType; Layout.preferredWidth: 135; model: ["Spending", "Saving"] }
                                TextField { id: plannedAmount; Layout.preferredWidth: 125; placeholderText: "Planned"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                                TextField {
                                    id: actualAmount
                                    Layout.preferredWidth: 125
                                    placeholderText: "Actual"
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                    color: text.length === 0 ? "#e8f7ff"
                                          : budgetType.currentText === "Spending"
                                            ? "#ff647c" : "#55e879"
                                    font.bold: text.length > 0
                                }
                                TextField { id: budgetNotes; Layout.fillWidth: true; placeholderText: "Notes (optional)" }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    Layout.fillWidth: true
                                    text: "Actual amounts drive the Actual remaining total."
                                    color: "#91adbf"
                                    font.pixelSize: 11
                                }
                                Button {
                                    text: "Cancel"
                                    flat: true
                                    visible: dashboard.editingMonthlyItemId >= 0
                                    onClicked: dashboard.cancelMonthlyEdit()
                                }
                                Button {
                                    text: dashboard.editingMonthlyItemId < 0 ? "Add category" : "Save changes"
                                    highlighted: true
                                    onClicked: {
                                        var saved = dashboard.editingMonthlyItemId < 0
                                                  ? budgetController.saveMonthlyItem(budgetName.text, budgetType.currentText, plannedAmount.text, actualAmount.text, budgetNotes.text)
                                                  : budgetController.updateMonthlyItem(dashboard.editingMonthlyItemId, budgetName.text, budgetType.currentText, plannedAmount.text, actualAmount.text, budgetNotes.text)
                                        if (saved)
                                            dashboard.cancelMonthlyEdit()
                                    }
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { Layout.fillWidth: true; text: budgetController.monthlyItems.length + " monthly categories"; color: "#91adbf" }
                        Button { text: "Copy previous month's plan"; visible: budgetController.monthlyItems.length === 0; onClicked: budgetController.copyPreviousMonth() }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 10
                        Layout.rightMargin: 6
                        spacing: 8
                        Label { Layout.fillWidth: true; text: "CATEGORY"; color: "#6f91a8"; font.pixelSize: 10; font.bold: true }
                        Label {
                            Layout.minimumWidth: dashboard.monthlyAmountColumnWidth
                            Layout.preferredWidth: dashboard.monthlyAmountColumnWidth
                            Layout.maximumWidth: dashboard.monthlyAmountColumnWidth
                            text: "PLANNED"
                            color: "#6f91a8"
                            font.pixelSize: 10
                            font.bold: true
                            horizontalAlignment: Text.AlignRight
                        }
                        Label {
                            Layout.minimumWidth: dashboard.monthlyAmountColumnWidth
                            Layout.preferredWidth: dashboard.monthlyAmountColumnWidth
                            Layout.maximumWidth: dashboard.monthlyAmountColumnWidth
                            text: "ACTUAL"
                            color: "#6f91a8"
                            font.pixelSize: 10
                            font.bold: true
                            horizontalAlignment: Text.AlignRight
                        }
                        Item {
                            Layout.minimumWidth: dashboard.monthlyActionsColumnWidth
                            Layout.preferredWidth: dashboard.monthlyActionsColumnWidth
                            Layout.maximumWidth: dashboard.monthlyActionsColumnWidth
                        }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 2
                        model: budgetController.monthlyItems
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: ListView.view.width
                            height: 56
                            radius: 6
                            color: index % 2 === 0 ? "#0c213a" : "#0a1d33"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 6
                                spacing: 8
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    Label { Layout.fillWidth: true; text: modelData.name + "  •  " + modelData.item_type; font.bold: true; elide: Text.ElideRight }
                                    Label { Layout.fillWidth: true; text: modelData.notes; color: "#91adbf"; font.pixelSize: 11; visible: text.length > 0; elide: Text.ElideRight }
                                }
                                Label {
                                    Layout.minimumWidth: dashboard.monthlyAmountColumnWidth
                                    Layout.preferredWidth: dashboard.monthlyAmountColumnWidth
                                    Layout.maximumWidth: dashboard.monthlyAmountColumnWidth
                                    text: modelData.planned
                                    color: "#91adbf"
                                    horizontalAlignment: Text.AlignRight
                                }
                                Label {
                                    Layout.minimumWidth: dashboard.monthlyAmountColumnWidth
                                    Layout.preferredWidth: dashboard.monthlyAmountColumnWidth
                                    Layout.maximumWidth: dashboard.monthlyAmountColumnWidth
                                    text: modelData.actual
                                    color: modelData.item_type === "Saving" ? "#55e879" : "#ff647c"
                                    font.bold: true
                                    horizontalAlignment: Text.AlignRight
                                }
                                RowLayout {
                                    Layout.minimumWidth: dashboard.monthlyActionsColumnWidth
                                    Layout.preferredWidth: dashboard.monthlyActionsColumnWidth
                                    Layout.maximumWidth: dashboard.monthlyActionsColumnWidth
                                    spacing: 4
                                    Button { Layout.fillWidth: true; text: "Edit"; flat: true; onClicked: dashboard.editMonthlyItem(modelData) }
                                    Button { Layout.fillWidth: true; text: "Remove"; flat: true; onClicked: budgetController.deleteMonthlyItem(modelData.id) }
                                }
                            }
                        }
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: budgetController.message
            color: "#ff647c"
            wrapMode: Text.WordWrap
            visible: text.length > 0
        }
    }
}

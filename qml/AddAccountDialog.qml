import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Dialog {
    id: dialog
    title: "Add account"
    modal: true
    anchors.centerIn: parent
    width: 380
    standardButtons: Dialog.Save | Dialog.Cancel

    property alias accountName: nameField.text
    property alias owner: ownerField.text
    property string accountType: typeField.currentText
    property alias balance: balanceField.text

    signal saveRequested()

    onAccepted: saveRequested()
    onOpened: nameField.forceActiveFocus()

    function clearFields() {
        nameField.clear()
        ownerField.clear()
        typeField.currentIndex = 0
        balanceField.clear()
    }

    Column {
        width: parent.width
        spacing: 12

        TextField {
            id: nameField
            width: parent.width
            placeholderText: "Account name"
        }

        TextField {
            id: ownerField
            width: parent.width
            placeholderText: "Owner"
        }

        ComboBox {
            id: typeField
            width: parent.width
            model: ["Bank", "Investment", "Retirement", "Real Estate", "Other Asset", "Debt"]
        }

        TextField {
            id: balanceField
            width: parent.width
            placeholderText: typeField.currentText === "Debt" ? "Current amount owed" : "Current balance"
            inputMethodHints: Qt.ImhFormattedNumbersOnly
        }
    }
}

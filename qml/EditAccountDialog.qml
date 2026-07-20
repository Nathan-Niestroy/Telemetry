import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Dialog {
    id: dialog
    title: "Edit family account"
    modal: true
    anchors.centerIn: parent
    width: 400
    standardButtons: Dialog.Save | Dialog.Cancel

    property int accountId: -1
    signal saveRequested(int accountId, string accountName, string owner,
                         string accountType, string balance)

    function edit(account) {
        accountId = account.id
        nameField.text = account.name
        ownerField.text = account.owner
        typeField.currentIndex = Math.max(0, typeField.find(account.account_type))
        balanceField.text = (account.balance_cents / 100).toFixed(2)
        open()
    }

    onAccepted: saveRequested(accountId, nameField.text, ownerField.text,
                              typeField.currentText, balanceField.text)
    onOpened: nameField.forceActiveFocus()

    Column {
        width: parent.width
        spacing: 12

        TextField { id: nameField; width: parent.width; placeholderText: "Account name" }
        TextField { id: ownerField; width: parent.width; placeholderText: "Owner" }
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

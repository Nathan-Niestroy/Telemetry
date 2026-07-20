import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Dialog {
    id: dialog
    title: "Gmail report settings"
    modal: true
    anchors.centerIn: parent
    width: 500
    standardButtons: Dialog.Cancel

    onOpened: {
        senderField.text = reportController.senderEmail
        appPasswordField.clear()
    }

    Column {
        width: parent.width
        spacing: 12

        Label {
            width: parent.width
            wrapMode: Text.WordWrap
            text: "Enter the Gmail address that sends family reports and its dedicated Google App Password. Your normal Gmail password is never used."
        }
        TextField {
            id: senderField
            width: parent.width
            placeholderText: "Gmail sending address"
            inputMethodHints: Qt.ImhEmailCharactersOnly | Qt.ImhNoAutoUppercase
        }
        TextField {
            id: appPasswordField
            width: parent.width
            placeholderText: "16-character Google App Password"
            echoMode: TextInput.Password
        }
        Label {
            width: parent.width
            wrapMode: Text.WordWrap
            text: reportController.message
            color: "#ff8a8a"
            visible: text.length > 0
        }
        Button {
            width: parent.width
            text: "Save securely"
            highlighted: true
            enabled: senderField.text.length > 0 && appPasswordField.text.length > 0
            onClicked: {
                if (reportController.saveSettings(senderField.text,
                                                  appPasswordField.text)) {
                    appPasswordField.clear()
                    dialog.close()
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Dialog {
    id: dialog
    title: "Preview family breakdown"
    modal: true
    anchors.centerIn: parent
    width: Math.min(720, parent.width - 48)
    height: Math.min(680, parent.height - 48)
    standardButtons: Dialog.Ok | Dialog.Cancel

    onOpened: {
        standardButton(Dialog.Ok).text = "Send email"
        previewArea.cursorPosition = 0
    }
    onAccepted: reportController.sendBreakdown()

    Column {
        anchors.fill: parent
        spacing: 10

        Label {
            width: parent.width
            text: "To: " + reportController.previewRecipients
            color: "#91adbf"
            elide: Text.ElideRight
        }
        Label {
            width: parent.width
            text: "Review the exact snapshot below before sending."
            color: "#91adbf"
        }
        ScrollView {
            id: previewScroll
            width: parent.width
            height: parent.height - 58
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn

            TextArea {
                id: previewArea
                width: previewScroll.availableWidth
                text: reportController.previewHtml
                textFormat: TextEdit.RichText
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                color: "#e8f7ff"
                padding: 16
                background: Rectangle {
                    color: "#0a1d33"
                    border.color: "#17466a"
                    radius: 8
                }
            }
        }
    }
}

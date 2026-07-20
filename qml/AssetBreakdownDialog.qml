import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Dialog {
    id: dialog
    title: overviewMode ? "All tracked holdings"
                        : "Holdings — " + selectedAccountName
    modal: true
    anchors.centerIn: parent
    width: 650
    height: Math.min(parent.height - 30, 700)
    standardButtons: Dialog.Close

    property bool isTsp: providerField.currentIndex === 1
    property bool isCash: providerField.currentIndex === 2
    property bool overviewMode: false
    property int selectedAccountId: -1
    property string selectedAccountName: ""
    property string searchText: ""
    property var filteredHoldings: accountController.holdings.filter(function(holding) {
        var accountMatches = dialog.overviewMode
                             || holding.account_id === dialog.selectedAccountId
        var query = dialog.searchText.trim().toLowerCase()
        var searchMatches = query.length === 0
                            || holding.symbol.toLowerCase().indexOf(query) >= 0
                            || holding.account_name.toLowerCase().indexOf(query) >= 0
                            || holding.provider_name.toLowerCase().indexOf(query) >= 0
        return accountMatches && searchMatches
    })

    function openForAccount(account) {
        overviewMode = false
        searchText = ""
        selectedAccountId = account.id
        selectedAccountName = account.name
        open()
    }

    function openOverview() {
        overviewMode = true
        selectedAccountId = -1
        selectedAccountName = ""
        searchText = ""
        open()
    }

    function editHolding(holding) {
        overviewMode = false
        if (holding.provider === "yahoo") {
            providerField.currentIndex = 0
            yahooSymbol.text = holding.symbol
        } else if (holding.provider === "tsp") {
            providerField.currentIndex = 1
            tspSymbol.currentIndex = Math.max(0, tspSymbol.find(holding.symbol))
            tspCloseField.clear()
        } else {
            providerField.currentIndex = 2
        }
        sharesField.text = holding.shares
        sharesField.forceActiveFocus()
    }

    Column {
        width: parent.width
        spacing: 12

        Label {
            width: parent.width
            text: dialog.overviewMode
                  ? "Search every fund, cash position, and account currently tracked by Telemetry."
                  : "Add the investments inside this account. Telemetry multiplies shares by the latest closing price."
            color: "#91adbf"
            wrapMode: Text.WordWrap
        }

        Row {
            width: parent.width
            spacing: 8
            visible: !dialog.overviewMode
            Rectangle {
                width: parent.width * 0.48
                height: providerField.height
                radius: 4
                color: "#102943"
                border.color: "#17466a"
                Label {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: dialog.selectedAccountName
                    font.bold: true
                }
            }
            ComboBox {
                id: providerField
                width: parent.width * 0.48
                model: ["Yahoo Finance", "TSP daily close", "Cash"]
            }
        }
        Row {
            width: parent.width
            spacing: 8
            visible: !dialog.overviewMode
            TextField {
                id: yahooSymbol
                width: parent.width * 0.30
                placeholderText: "Ticker"
                visible: !dialog.isTsp && !dialog.isCash
                font.capitalization: Font.AllUppercase
            }
            ComboBox {
                id: tspSymbol
                width: parent.width * 0.30
                visible: dialog.isTsp
                model: ["G Fund", "F Fund", "C Fund", "S Fund", "I Fund",
                        "L Income", "L 2030", "L 2035", "L 2040", "L 2045",
                        "L 2050", "L 2055", "L 2060", "L 2065", "L 2070", "L 2075"]
            }
            TextField {
                id: sharesField
                width: parent.width * 0.30
                placeholderText: dialog.isCash ? "Cash amount" : "Shares"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
        }
        Row {
            width: parent.width
            spacing: 8
            visible: !dialog.overviewMode && dialog.isTsp
            TextField {
                id: tspCloseField
                width: parent.width * 0.48
                placeholderText: "Manual close (optional)"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
            TextField {
                id: tspDateField
                width: parent.width * 0.48
                placeholderText: "Manual price date"
                text: Qt.formatDate(new Date(), "yyyy-MM-dd")
            }
        }

        Button {
            width: parent.width
            text: "Add or update holding"
            highlighted: true
            visible: !dialog.overviewMode
            enabled: dialog.selectedAccountId >= 0 && sharesField.text.length > 0
                     && (dialog.isTsp || dialog.isCash || yahooSymbol.text.length > 0)
            onClicked: {
                var provider = dialog.isTsp ? "tsp" : (dialog.isCash ? "cash" : "yahoo")
                var symbol = dialog.isTsp ? tspSymbol.currentText
                                          : (dialog.isCash ? "CASH" : yahooSymbol.text)
                if (accountController.saveHolding(dialog.selectedAccountId, provider,
                                                  symbol, sharesField.text,
                                                  tspCloseField.text, tspDateField.text)) {
                    yahooSymbol.clear()
                    sharesField.clear()
                    tspCloseField.clear()
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: "#17466a" }

        TextField {
            width: parent.width
            visible: dialog.overviewMode
            placeholderText: "Search by fund, account, or provider"
            text: dialog.searchText
            onTextChanged: dialog.searchText = text
        }

        Row {
            width: parent.width
            Label { width: parent.width - refreshButton.width; text: "TRACKED HOLDINGS"; color: "#55dff4"; font.bold: true }
            Button {
                id: refreshButton
                text: accountController.refreshingPrices ? "Refreshing…" : "Refresh closing prices"
                enabled: !accountController.refreshingPrices && dialog.filteredHoldings.length > 0
                onClicked: accountController.refreshMarketPrices()
            }
        }

        Label {
            width: parent.width
            text: dialog.overviewMode
                  ? dialog.filteredHoldings.length + " of " + accountController.holdings.length + " positions shown"
                  : "Yahoo tickers and official TSP closes refresh automatically. Cash stays at its entered dollar amount."
            color: "#91adbf"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        ListView {
            id: holdingsList
            width: parent.width
            height: Math.max(170, dialog.height
                             - (dialog.overviewMode ? 285 : (dialog.isTsp ? 500 : 440)))
            clip: true
            spacing: 5
            model: dialog.filteredHoldings
            interactive: contentHeight > height
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {
                policy: holdingsList.contentHeight > holdingsList.height
                        ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
            }

            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 60
                radius: 8
                color: "#0c213a"
                Row {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 9
                    Column {
                        width: parent.width - valueLabel.width
                               - (dialog.overviewMode ? 20
                                  : editButton.width + removeButton.width + 30)
                        Label { text: modelData.symbol + "  •  " + modelData.account_name; font.bold: true }
                        Label {
                            text: (modelData.provider === "cash"
                                   ? "$" + modelData.shares_display + " cash"
                                   : modelData.shares_display + " shares  •  " + modelData.provider_name
                                     + (modelData.price_as_of ? "  •  close " + modelData.price_as_of : "  •  not refreshed"))
                            color: "#91adbf"; font.pixelSize: 11
                        }
                    }
                    Label {
                        id: valueLabel
                        width: 105
                        anchors.verticalCenter: parent.verticalCenter
                        horizontalAlignment: Text.AlignRight
                        text: modelData.market_value
                        color: "#55e879"; font.bold: true
                    }
                    Button {
                        id: editButton
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Edit"
                        visible: !dialog.overviewMode
                        onClicked: dialog.editHolding(modelData)
                    }
                    Button {
                        id: removeButton
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Remove"
                        visible: !dialog.overviewMode
                        onClicked: accountController.deleteHolding(modelData.id)
                    }
                }
            }
        }

        Label {
            width: parent.width
            text: accountController.message
            color: accountController.message.indexOf("Updated") === 0 ? "#55e879" : "#ff647c"
            wrapMode: Text.WordWrap
            visible: text.length > 0
        }
    }
}

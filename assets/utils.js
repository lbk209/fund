window.calculateCAGR = function(data_tkr) {
    if (!data_tkr || Object.keys(data_tkr).length < 2) return "Invalid data";

    // Convert date keys to an array and sort them in ascending order
    let dates = Object.keys(data_tkr).sort();
    
    // First and last values
    let initialValue = data_tkr[dates[0]];
    let finalValue = data_tkr[dates[dates.length - 1]];

    // Compute number of months between first and last date
    let startDate = new Date(dates[0]);
    let endDate = new Date(dates[dates.length - 1]);
    let months = (endDate.getFullYear() - startDate.getFullYear()) * 12 + (endDate.getMonth() - startDate.getMonth());

    // Convert months to years
    let years = months / 12;
    if (years <= 0) return "Time period too short";

    // Calculate CAGR
    let cagr = (finalValue / initialValue) ** (1 / years) - 1;

    // Format as percentage
    //return "CAGR: " + (cagr * 100).toFixed(2) + "%";
    return (cagr * 100);
};


window.normalizePrice = function(data_tickers, basePrc = 1000) {
    // Extract tickers (fund names)
    let tickers = Object.keys(data_tickers);

    // Collect all unique dates across all tickers
    let allDates = new Set();
    for (let tkr of tickers) {
        Object.keys(data_tickers[tkr]).forEach(date => allDates.add(date));
    }

    // Sort dates in ascending order
    let dates = Array.from(allDates).sort();

    // Find the first date where all tickers have valid values
    let startIndex = dates.findIndex(date => 
        tickers.every(tkr => 
            data_tickers[tkr][date] !== null && 
            data_tickers[tkr][date] !== undefined &&
            !isNaN(data_tickers[tkr][date])
        )
    );

    if (startIndex === -1) return data_tickers; // No valid start date found

    let startDate = dates[startIndex];

    // Compute the normalized values with the same structure as the input
    let result = {};
    for (let tkr of tickers) {
        result[tkr] = {};
        for (let i = startIndex; i < dates.length; i++) {
            let date = dates[i];
            if (data_tickers[tkr][startDate] !== null && data_tickers[tkr][startDate] !== undefined) {
                result[tkr][date] = (data_tickers[tkr][date] / data_tickers[tkr][startDate]) * basePrc;
            } else {
                result[tkr][date] = null;
            }
        }
    }

    return result;
};


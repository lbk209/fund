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


window.selectTickers = function(option, tickers, data_rank, num = 10) {
    // Filter tickers that exist in data_rank
    let validTickers = tickers.filter(ticker => data_rank.hasOwnProperty(ticker));
    
    if (option === "Top") {
        return validTickers
            .sort((a, b) => data_rank[a] - data_rank[b]) // Ascending order (lower rank is better)
            .slice(0, num);
    }
    
    if (option === "Bottom") {
        return validTickers
            .sort((a, b) => data_rank[b] - data_rank[a]) // Descending order (higher rank is worse)
            .slice(0, num);
    }
    
    if (option === "Random") {
        return validTickers
            .sort(() => Math.random() - 0.5) // Shuffle tickers randomly
            .slice(0, num);
    }
    
    return []; // Return empty array if option is invalid
}


window.updateLayout = function(layout, x = 0, y = -0.5, width = 768) {
    // Detect the window width (client-side)
    const viewportWidth = window.innerWidth;
    if (viewportWidth < width) {
        // Adjust legend position for mobile devices
        layout.legend = {
            ...layout.legend, // Preserve existing legend properties
            orientation: 'h',  // Horizontal legend
            x: x,              // Align legend to the left
            y: y,           // Position legend below the plot
            xanchor: 'left',   // Anchor legend's x position to the left
            yanchor: 'top',    // Anchor legend's y position to the top
        };
        layout.yaxis = {...layout.yaxis, automargin: true,};
        layout.margin = {
            ...layout.margin,
            //l: layout.margin?.l || 10,  // Left margin
            l: 0,
            r: 0,  // Right margin
            //t: layout.margin?.t || 0,  // Preserve the top margin if set, or default to 0
            //b: layout.margin?.b || 0   // Preserve the bottom margin if set, or default to 0
        };
    }
    return layout;
}
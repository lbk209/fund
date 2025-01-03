import pymc as pm
import arviz as az
import pytensor.tensor as pt
import numpy as np
import pandas as pd
import os, pickle, re
import matplotlib as mpl
import matplotlib.pyplot as plt
from os.path import splitext
from matplotlib.gridspec import GridSpec

# support korean lang
mpl.rcParams['axes.unicode_minus'] = False
plt.rcParams["font.family"] = 'NanumBarunGothic'

METRICS = [
    'total_return', 'cagr', 'calmar', 
    'max_drawdown', 'avg_drawdown', 'avg_drawdown_days', 
    'daily_vol', 'daily_sharpe', 'daily_sortino', 
    'monthly_vol', 'monthly_sharpe', 'monthly_sortino'
]


def set_filename(file, ext=None, default='test'):
    """
    return default for file name if file is None
    set extension if no extension in file
    defaule: ex) 'temp.csv', 'temp', None
    ext: ex) '.csv', 'csv', None
    """
    # set dault file name and extension
    if default is not None:
        name, _ext = splitext(default)
        ext = _ext if ext is None else ext
        ext = ext.replace('.', '')
    # return default if file is None
    if file is None:
        if default is not None:
            default = name if ext is None else f'{name}.{ext}'
        return default
    # set ext if no ext in file    
    name, _ext = splitext(file)
    if len(_ext) == 0:
        file = name if ext is None else f'{name}.{ext}'
    return file


def create_split_axes(figsize=(10, 6), vertical_split=True, 
                      ratios=(3, 1), share_axis=False, space=0):
    """
    Creates a figure with two subplots arranged either vertically or horizontally.

    Parameters:
    -----------
    figsize : tuple, optional
        The size of the figure (width, height) in inches. Default is (10, 6).
    vertical_split : bool, optional
        If True, splits the figure vertically (stacked subplots).
        If False, splits the figure horizontally (side-by-side subplots). Default is True.
    ratios : tuple, optional
        Ratios of the sizes of the two subplots. Default is (3, 1).
    share_axis : bool, optional
        If True, the axes will share either the x-axis (for vertical split) or the y-axis (for horizontal split).
        Default is True.

    Returns:
    --------
    tuple
        A tuple containing the two subplot axes (ax1, ax2).

    Example:
    --------
    >>> ax1, ax2 = create_split_axes(figsize=(12, 8), vertical_split=False, ratios=(2, 1), share_axis=False)
    """
    fig = plt.figure(figsize=figsize)
    if vertical_split:
        gs = GridSpec(2, 1, figure=fig, hspace=space, height_ratios=ratios)
        sp1 = gs[:-1, :]
        sp2 = gs[-1, :]
    else:
        gs = GridSpec(1, 2, figure=fig, wspace=space, width_ratios=ratios)
        sp1 = gs[:, :-1]
        sp2 = gs[:, -1]
        
    ax1 = fig.add_subplot(sp1)
    ax2 = fig.add_subplot(sp2)
    
    if share_axis:
        if vertical_split:
            ax1.sharex(ax2)
        else:
            ax1.sharey(ax2)
    
    return (ax1, ax2)


def string_shortener(x, n=20, r=1, ellipsis="..."):
    """
    Clips a string to a specified length, inserting an ellipsis ('...') 
     and cleaning up any surrounding special characters to ensure a tidy output.
    """
    if len(x) <= n:
        return x

    if r == 1:
        result = f"{x[:n]}{ellipsis}"
    elif r == 0:
        result = f"{ellipsis}{x[-n:]}"
    else:
        n1 = int(n * r)
        n2 = int(n * (1 - r))
        result = f"{x[:n1]}{ellipsis}{x[-n2:]}"

    # Remove special characters immediately surrounding the custom ellipsis
    result = re.sub(r"([^a-zA-Z0-9\s])" + re.escape(ellipsis), f"{ellipsis}", result)  # Before the ellipsis
    result = re.sub(re.escape(ellipsis) + r"([^a-zA-Z0-9\s])", f"{ellipsis}", result)  # After the ellipsis
    return result


class BayesianEstimator():
    def __init__(self, df_prices, days_in_year=252, metrics=METRICS, security_names=None):
        # df of tickers (tickers in columns) which of each might have its own periods.
        # the periods of all tickers will be aligned in every calculation.
        df_prices = df_prices.to_frame() if isinstance(df_prices, pd.Series) else df_prices
        self.df_prices = df_prices
        self.days_in_year = days_in_year
        self.metrics = metrics
        self.bayesian_data = None
        self.security_names = security_names


    @staticmethod
    def create(file, path='.', **kwargs):
        """
        create instance from sampled
        kwargs: kwargs of __init__
        """
        bayesian_data = BayesianEstimator._load(file, path)
        df_prices = bayesian_data['data']
        be = BayesianEstimator(df_prices, **kwargs)
        be.bayesian_data = bayesian_data
        return be
        

    def get_stats(self, metrics=None, sort_by=None, align_period=False, idx_dt=['start', 'end']):
        metrics = [metrics] if isinstance(metrics, str) else metrics
        metrics = self._check_var(metrics, self.metrics)
        df_prices = self.df_prices
        return performance_stats(df_prices, metrics=metrics, sort_by=sort_by, align_period=align_period, idx_dt=idx_dt)

        
    def plot_historical(self, figsize=(10,4), title='Portfolio Growth'):
        """
        plot total value of portfolio
        """
        df_prices = self.df_prices
        ax = df_prices.plot(figsize=figsize, title=title)
        ax.autoscale(enable=True, axis='x', tight=True)
        return None
        

    def get_freq_days(self, freq='1Y'):
        """
        freq: str or int
        """
        if isinstance(freq, str):
            # split freq to int & unit
            n_t = BacktestManager.split_int_n_temporal(freq, 'M') # default month
        else: # return int regardless of unit
            return freq
        if n_t is None:
            return
        else:
            n, temporal = n_t        
            
        days_in_year = self.days_in_year
        cond = lambda x, y: False if x is None else x[0].lower() == y[0].lower()
        if cond(temporal, 'W'):
            n *= round(days_in_year / WEEKS_IN_YEAR)
        elif cond(temporal, 'M'):
            n *= round(days_in_year / 12)
        elif cond(temporal, 'Q'):
            n *= round(days_in_year / 4)
        elif cond(temporal, 'Y'):
            n *= days_in_year
        return n


    def _check_var(self, arg, arg_self):
        return arg_self if arg is None else arg

        
    def _calc_mean_return(self, df_prices, periods):
        return df_prices.apply(lambda x: x.pct_change(periods).dropna().mean())
        

    def _calc_volatility(self, df_prices, periods):
        return df_prices.apply(lambda x: x.pct_change(periods).dropna().std())
        

    def _calc_sharpe(self, df_prices, periods, rf=0):
        mean = self._calc_mean_return(df_prices, periods)
        std = self._calc_volatility(df_prices, periods)
        return (mean - rf) / std


    def get_ref_val(self, freq='1y', rf=0, align_period=False):
        """
        get ref val for 
        """
        df_prices = self.df_prices
        if align_period:
            df_prices = self.align_period(df_prices, axis=0, fill_na=True)
        periods = self.get_freq_days(freq)
        args = [df_prices, periods]
        return {
            #'mean': self._calc_mean_return(*args).to_dict(),
            #'std': self._calc_volatility(*args).to_dict(),
            'ror': self._calc_mean_return(*args).to_dict(),
            'sharpe': self._calc_sharpe(*args).to_dict(),
            'cagr': self._calc_mean_return(df_prices, self.days_in_year).to_dict()
        }


    def bayesian_sample(self, freq='1y', rf=0, align_period=False,
                        sample_draws=1000, sample_tune=1000, target_accept=0.9,
                        multiplier_std=1000, rate_nu = 29, normality_sharpe=True,
                        file=None, path='.'):
        """
        normality_sharpe: set to True if 
         -. You are making comparisons to Sharpe ratios calculated under the assumption of normality.
         -. You want to account for the higher variability due to the heavy tails of the t-distribution.
        """
        days_in_year = self.days_in_year
        periods = self.get_freq_days(freq)
        df_prices = self.df_prices
        tickers = list(df_prices.columns)
        
        if align_period:
            df_prices = self.align_period(df_prices, axis=0, fill_na=True)
            df_ret = df_prices.pct_change(periods).dropna()
            mean_prior = df_ret.mean()
            std_prior = df_ret.std()
            std_low = std_prior / multiplier_std
            std_high = std_prior * multiplier_std
        else:
            ret_list = [df_prices[x].pct_change(periods).dropna() for x in tickers]
            mean_prior = [x.mean() for x in ret_list]
            std_prior = [x.std() for x in ret_list]
            std_low = [x / multiplier_std for x in std_prior]
            std_high = [x * multiplier_std for x in std_prior]
            ror = dict()
        
        coords={'ticker': tickers}
        with pm.Model(coords=coords) as model:
            # nu: degree of freedom (normality parameter)
            nu = pm.Exponential('nu_minus_two', 1 / rate_nu, testval=4) + 2.
            mean = pm.Normal('mu', mu=mean_prior, sigma=std_prior, dims='ticker')
            std = pm.Uniform('sig', lower=std_low, upper=std_high, dims='ticker')
            
            if align_period:
                ror = pm.StudentT('ror', nu=nu, mu=mean, sigma=std, observed=df_ret)
            else:
                func = lambda x: dict(mu=mean[x], sigma=std[x], observed=ret_list[x])
                ror = {i: pm.StudentT(f'ror[{x}]', nu=nu, **func(i)) for i, x in enumerate(tickers)}
    
            #pm.Deterministic('mean', mean, dims='ticker')
            #pm.Deterministic('std', std, dims='ticker')
            std_sr = std * pt.sqrt(nu / (nu - 2)) if normality_sharpe else std
            ror = pm.Normal('ror', mu=mean, sigma=std_sr, dims='ticker')
            sharpe = pm.Deterministic('sharpe', (mean-rf) / std_sr, dims='ticker')

            years = periods/days_in_year
            cagr = pm.Deterministic('cagr', (ror+1) ** (1/years) - 1, dims='ticker')
            yearly_sharpe = pm.Deterministic('yearly_sharpe', sharpe * np.sqrt(1/years), dims='ticker')
    
            trace = pm.sample(draws=sample_draws, tune=sample_tune,
                              #chains=chains, cores=cores,
                              target_accept=target_accept,
                              #return_inferencedata=False, # TODO: what's for?
                              progressbar=True)
            
        self.bayesian_data = {'trace':trace, 'coords':coords, 'align_period':align_period, 
                              'freq':freq, 'rf':rf, 'data':df_prices}
        if file:
            self.save(file, path)
        return None


    def save(self, file, path='.'):
        """
        save bayesian_data of bayesian_sample 
        """
        if self.bayesian_data is None:
            return print('ERROR: run bayesian_sample first')
    
        file = set_filename(file, 'pkl')
        f = os.path.join(path, file)
        if os.path.exists(f):
            return print(f'{f} exists')
        with open(f, 'wb') as handle:
            pickle.dump(self.bayesian_data, handle)
        return print(f'{f} saved')

                
    @staticmethod
    def _load(file, path='.'):
        """
        load bayesian_data of bayesian_sample 
        """
        file = set_filename(file, 'pkl')
        f = os.path.join(path, file)
        if not os.path.exists(f):
            return print(f'{f} does not exist')
        with open(f, 'rb') as handle:
            bayesian_data = pickle.load(handle)
        print(f'{f} loaded')
        return bayesian_data
        
    
    def bayesian_summary(self, var_names=None, filter_vars='like', **kwargs):
        if self.bayesian_data is None:
            return print('ERROR: run bayesian_sample first')
        else:
            trace = self.bayesian_data['trace']
            df = az.summary(trace, var_names=var_names, filter_vars=filter_vars, **kwargs)
            # split index to metric & ticker to make them new index
            index = ['metric', 'ticker']
            func = lambda x: re.match(r"(.*)\[(.*)\]", x).groups()
            df[index] = df.apply(lambda x: func(x.name), axis=1, result_type='expand')
            return df.set_index(index)


    def plot_posterior(self, var_names=None, tickers=None, ref_val=None, 
                       length=20, ratio=1, textsize=9, **kwargs):
        """
        ref_val: None, float or 'default'
        """
        if self.bayesian_data is None:
            return print('ERROR: run bayesian_sample first')
        else:
            trace = self.bayesian_data['trace']
            coords = self.bayesian_data['coords']
            freq = self.bayesian_data['freq']
            rf = self.bayesian_data['rf']
            align_period = self.bayesian_data['align_period']
            security_names = self.security_names
    
        if tickers is not None:
            tickers = [tickers] if isinstance(tickers, str) else tickers
            coords = {'ticker': tickers}
    
        if ref_val == 'default':
            ref_val = self.get_ref_val(freq=freq, rf=rf, align_period=align_period)
            col_name = list(coords.keys())[0]
            ref_val = {k: [{col_name:at, 'ref_val':rv} for at, rv in v.items()] for k,v in ref_val.items()}
        #ref_val.update({'ror': [{'ref_val': 0}], 'cagr': [{'ref_val': 0}]})
    
        axes = az.plot_posterior(trace, var_names=var_names, filter_vars='like', coords=coords,
                                ref_val=ref_val, textsize=textsize, **kwargs)
        n_r, n_c = axes.shape
        for i in range(n_r):
            for j in range(n_c):
                ax = axes[i][j]
                t = ax.get_title()
                if t == '':
                    continue
                else:
                    title = t.split('\n')[1]
                if security_names is not None:
                    clip = lambda x: string_shortener(x, n=length, r=ratio)
                    title = clip(security_names[title])
                ax.set_title(title, fontsize=textsize)
        #return ref_val
        return None


    def plot_returns(self, tickers=None, num_samples=None, var_names=['cagr', 'yearly_sharpe'],
                     figsize=(10,3), xlim=(-0.4, 0.6), length=20, ratio=1, max_legend=99):
        """
        var_names: ['ror', 'sharpe'] or ['cagr', 'yearly_sharpe']
        """
        security_names = self.security_names
        axes = create_split_axes(figsize=figsize, vertical_split=False, 
                                 ratios=(1, 1), share_axis=False, space=0.05)
        
        axes = self._plot_compare(var_names, tickers=tickers, num_samples=num_samples, 
                                  figsize=figsize, axes=axes)
        if axes is None:
            return None # see _plot_compare for err msg
            
        ax1, ax2 = axes
        _ = ax1.set_title(var_names[0].upper())
        _ = ax1.set_xlim(xlim)
        _ = ax1.axvline(0, c='grey', lw=1, ls='--')
        _ = ax1.get_legend().remove()
        _ = ax2.set_title(var_names[1].upper())

        legend = ax2.get_legend_handles_labels()[1]
        if security_names is not None:
            clip = lambda x: string_shortener(x, n=length, r=ratio)
            legend = [clip(security_names[x]) for x in legend]
        _ = ax2.legend(legend[:max_legend], bbox_to_anchor=(1.0, 1.0), loc='upper left')
        
        _ = [ax.set_yticks([]) for ax in axes]
        _ = [ax.set_ylabel(None) for ax in axes]
        return axes

    
    def _plot_compare(self, var_names, tickers=None, num_samples=None, figsize=(6,5), axes=None):
        if self.bayesian_data is None:
            return print('ERROR: run bayesian_sample first')
        else:
            trace = self.bayesian_data['trace']
    
        if isinstance(var_names, str):
            var_names = [var_names]
        if (tickers is not None) and isinstance(tickers, str):
            tickers = [tickers]
            
        stacked = az.extract(trace, num_samples=num_samples)
        vn = [x for x in var_names if x not in stacked.keys()]
        if len(vn) > 0:
            v = ', '.join(var_names)
            return print(f'ERROR: Check if {v} exit')

        if axes is None:
            fig, axes = plt.subplots(1, len(var_names), figsize=figsize)
        for i, v in enumerate(var_names):
            df = stacked[v].to_dataframe()
            df = (df[v].droplevel(['chain','draw'])
                       .reset_index().pivot(columns="ticker")
                       .droplevel(0, axis=1))
            df = df[tickers] if tickers is not None else df
            _ = df.plot.kde(ax=axes[i])
        return axes
        

    def plot_trace(self, var_names=None, filter_vars='like', legend=False, figsize=(12,6), **kwargs):
        if self.bayesian_data is None:
            return print('ERROR: run bayesian_sample first')
        else:
            trace = self.bayesian_data['trace']
            return az.plot_trace(trace, var_names=var_names, filter_vars=filter_vars, 
                                 legend=legend, figsize=figsize, **kwargs)


    def plot_energy(self, **kwargs):
        if self.bayesian_data is None:
            return print('ERROR: run bayesian_sample first')
        else:
            trace = self.bayesian_data['trace']
            return az.plot_energy(trace, **kwargs)


    def align_period(self, df, axis=0, fill_na=True, **kwargs):
        return align_period(df, axis=axis, fill_na=fill_na, **kwargs)
import yfinance as yf

def download_data():
    df = yf.download('SPY', period='10y', interval='1d')
    df.columns = df.columns.droplevel('Ticker')
    df.columns.name = None
    return df

def validate_data(df):
    cols_list = ['Open','High','Low','Close','Volume']
    missing_list = []

    if not set(cols_list).issubset(df.columns):    
        for i in cols_list:
            if i not in df.columns:
                missing_list.append(i)            
        raise KeyError(f'Key Column/s missing:- {missing_list}')
    
    elif df.isna().any().any() > 0:
        ndf = df[df.isna().any(axis=1)]
        na_index = ndf.index[0].strftime('%Y-%m-%d')
        na_cols = ndf.columns[ndf.iloc[0].isna()].tolist()
        raise ValueError(f"'NA' Value/s detected, {len(ndf)} rows affected.\nFirst occurrence:- Date: {na_index} | Column/s affected: {na_cols}")
    
    elif df.index.duplicated().any():
        dup_dates_list = df.index[df.index.duplicated(keep=False)].strftime('%Y-%m-%d').unique().tolist()
        raise ValueError(f'Duplicate Date/s detected!:- {dup_dates_list}')
    
    elif (df['High'] < df['Open']).any():  
        indx = df.index[(df['High'] < df['Open'])]
        opn = df.loc[indx,'Open']
        high = df.loc[indx, 'High']
        raise ValueError(f'Invalid High data at {len(indx)} instance/s\nFirst occurrence:- Date: {indx[0]} | High: {high[0]} | Open: {opn[0]}')
    
    elif (df['High'] < df['Close']).any():
        indx2 = df.index[(df['High'] < df['Close'])]
        close = df.loc[indx2,'Close']
        high2 = df.loc[indx2, 'High']
        raise ValueError(f'Invalid High data at {len(indx2)} instance/s\nFirst occurrence:- Date: {indx2[0]} | High: {high2[0]} | Close {close[0]}')

    elif (df['Low'] > df['Open']).any():  
        indx3 = df.index[(df['Low'] > df['Open'])]
        opn2 = df.loc[indx3,'Open']
        low = df.loc[indx3, 'Low']
        raise ValueError(f'Invalid Low data at {len(indx3)} instance/s\nFirst occurrence:- Date: {indx3[0]} | Low: {low[0]} | Open: {opn2[0]}')

    elif (df['Low'] > df['Close']).any():  
        indx4 = df.index[(df['Low'] > df['Close'])]
        close2 = df.loc[indx4,'Close']
        low2 = df.loc[indx4, 'Low']
        raise ValueError(f'Invalid Low data at {len(indx4)} instance/s\nFirst occurrence:- Date: {indx4[0]} | Low: {low2[0]} | Close: {close2[0]}')

    elif  (df[['Close','High','Low','Open']] <= 0).any().any():
        neg_df = df.loc[(df[['Close','High','Low','Open']] <= 0).any(axis=1)].copy()
        neg_df.drop(columns=['Volume'], inplace=True)
        neg_cols = neg_df.columns[neg_df.iloc[0] <= 0].tolist()
        neg_prices = neg_df.loc[neg_df.index[0], neg_cols].tolist()
        raise ValueError(f'Invalid Price detected at {len(neg_df)} instance/s.\nFirst occurrence at Date: {neg_df.index[0]} | Column/s affected: {neg_cols} | Price/s: {neg_prices}')
    
    elif  (df['Volume'] <= 0).any():
        vdf = df.loc[df['Volume'] <= 0].copy()
        vdf.drop(columns=['Close','High','Low','Open'], inplace=True)
        raise ValueError(f'Invalid Volume detected at {len(vdf)} instance/s.\nFirst occurrence at Date: {vdf.index[0]} | Volume: {vdf.iloc[0].tolist()}')
    return True

def save_data(df, filepath):
    df.to_csv(filepath)

if __name__ == "__main__":
    df = download_data()
    validate_data(df)
    save_data(df, "data/SPY.csv")



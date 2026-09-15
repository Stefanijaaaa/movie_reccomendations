import pickle
from datetime import date
import random
import math
import os
from collections import defaultdict

class UserItemData:
    def __init__(self, path, start_date=None, end_date=None, min_ratings=0, use_pickle=True):
        self.path = path
        self.from_date = start_date
        self.to_date = end_date
        self.min_ratings = min_ratings
        self.ratings = 0
        self.user_ratings = {}  # {user_id: {movie_id: rating}}
        self.movies = set()
        self.use_pickle = use_pickle
        self.pickle_path = f"{self.path}.pkl"

        if use_pickle and os.path.exists(self.pickle_path):
            with open(self.pickle_path, 'rb') as f:
                data = pickle.load(f)
                self.user_ratings = data['user_ratings']
                self.movies = data['movies']
                self.ratings = data['ratings']
        else:
            self._read_file()
            if use_pickle:
                with open(self.pickle_path, 'wb') as f:
                    pickle.dump({
                        'user_ratings': self.user_ratings,
                        'movies': self.movies,
                        'ratings': self.ratings
                    }, f)

    def _read_file(self):
        movie_counts = {}

        # changing date format so i can actually compare
        if self.from_date:
            parts = self.from_date.split(".")
            self.from_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
        if self.to_date:
            parts = self.to_date.split(".")
            self.to_date = date(int(parts[2]), int(parts[1]), int(parts[0]))

        with open(self.path, 'r') as f:
            next(f)
            for line in f:
                parts = line.split('\t')
                user_id = int(parts[0])
                movie_id = int(parts[1])
                rating = float(parts[2])
                day, month, year = int(parts[3]), int(parts[4]), int(parts[5])
                review_date = date(year, month, day)

                # date filtering
                if self.from_date and review_date < self.from_date:
                    continue
                if self.to_date and review_date >= self.to_date:
                    continue

                movie_counts[movie_id] = movie_counts.get(movie_id, 0) + 1

                if user_id not in self.user_ratings:
                    self.user_ratings[user_id] = {}
                self.user_ratings[user_id][movie_id] = rating
                self.movies.add(movie_id)

        # weeding out the movies with less
        if self.min_ratings > 0:
            valid_movies = set()
            for movie_id in movie_counts:
                if movie_counts[movie_id] >= self.min_ratings:
                    valid_movies.add(movie_id)
            
            for user_id in list(self.user_ratings.keys()):
                for movie_id in list(self.user_ratings[user_id].keys()):
                    if movie_id not in valid_movies:
                        del self.user_ratings[user_id][movie_id]
                
                if len(self.user_ratings[user_id]) == 0:
                    del self.user_ratings[user_id]
            
            self.movies = valid_movies
    
        total = 0
        for user_id in self.user_ratings:
            total = total + len(self.user_ratings[user_id])
        self.ratings = total

    def nratings(self):
        return self.ratings
    

class MovieData:
    def __init__(self, path, use_pickle=True):
        self.path = path
        self.use_pickle = use_pickle
        self.pickle_path = f"{self.path}.pkl"
        self.movies = {}

        if use_pickle and os.path.exists(self.pickle_path):
            with open(self.pickle_path, 'rb') as f:
                self.movies = pickle.load(f)
        else:
            self._read_file()
            if use_pickle:
                with open(self.pickle_path, 'wb') as f:
                    pickle.dump(self.movies, f)

    def _read_file(self):
        # got some error have to encode??
        with open(self.path, 'r', encoding='ISO-8859-1') as f:
            next(f)
            for line in f:
                parts = line.strip().split('\t')
                movie_id = int(parts[0])
                movie_title = parts[1]
                self.movies[movie_id] = movie_title

    def get_title(self, movieID):
        return self.movies.get(movieID, None)



class RandomPredictor:
    def __init__(self, min_rating, max_rating):
        self.min = min_rating
        self.max = max_rating
        self.movies = set()

    def fit(self, X):
        self.movies = X.movies

    def predict(self, user_id):
        predictions = {}
    
        for movie_id in self.movies:
            predictions[movie_id] = random.randint(self.min, self.max)
    
        return predictions


class Recommender:
    def __init__(self, predictor):
        self.predictor = predictor
        self.X = None

    def fit(self, X):
        self.X = X
        self.predictor.fit(X)

    def recommend(self, userID, n=10, rec_seen=True):
        predicted = self.predictor.predict(userID)

        # if maybe we shouldnt reccomend
        if not rec_seen:
            user_movies = self.X.user_ratings.get(userID, {})
            seen = set(user_movies.keys())
            filtered_predictions = {}

            for movie_id in predicted:
                    if movie_id not in seen:
                        filtered_predictions[movie_id] = predicted[movie_id]

            # replacing it back so it works either way
            predicted = filtered_predictions
        sorted_list = sorted(predicted.items(), key=lambda x: x[1], reverse=True)
        return sorted_list[:n]

class AveragePredictor:
    def __init__(self, b=0):
        self.b = b
        self.movie_avg = {}
    
    def fit(self, X):
        movie_ratings = {}
        for user_id in X.user_ratings:
            for movie_id, rating in X.user_ratings[user_id].items():
                if movie_id not in movie_ratings:
                    movie_ratings[movie_id] = []
                movie_ratings[movie_id].append(rating)
        
        total_sum = 0
        total_count = 0
        for ratings in movie_ratings.values():
            total_sum += sum(ratings)
            total_count += len(ratings)
        global_avg = total_sum / total_count
        
        for movie, ratings in movie_ratings.items():
            vs = sum(ratings)
            n = len(ratings)
            avg = (vs + self.b * global_avg) / (n + self.b)
            self.movie_avg[movie] = avg
    
    # i still dont understand what to do with user_id??? 
    def predict(self, user_id):
        return self.movie_avg
    
class ViewsPredictor:
    def __init__(self):
        self.movie_views = {}
    
    def fit(self, X):
        # COUNTING HOW MANY TISE IT HAS BEEN  VIEWS
        for user_id in X.user_ratings:
            for movie_id in X.user_ratings[user_id]:
                if movie_id not in self.movie_views:
                    self.movie_views[movie_id] = 0
                self.movie_views[movie_id] += 1
    
    # user_id for whaaattt??? T^T 
    def predict(self, user_id):
        return self.movie_views


class ItemBasedPredictor:
    def __init__(self, min_values=0, threshold=0, use_pickle=True):
        self.min_values = min_values  # minimum common users
        self.threshold = threshold
        self.use_pickle = use_pickle
        self.sim_pickle = f"item_based_sim_min{min_values}_th{threshold}.pkl"

    def fit(self, X):
        self.X = X

      
        self.movie_ratings = {}
        for user_id, ratings in X.user_ratings.items():
            for movie_id, rating in ratings.items():
                if movie_id not in self.movie_ratings:
                    self.movie_ratings[movie_id] = {}
                self.movie_ratings[movie_id][user_id] = rating

        # user averages
        self.user_avg = {u: sum(r.values())/len(r) for u, r in X.user_ratings.items() if r}

        # movies to consider
        self.filter = set(self.movie_ratings.keys())

        # compute similarities
        self.similarities = {}
        movies = list(self.movie_ratings.keys())
        for i in range(len(movies)):
            for j in range(i+1, len(movies)):
                m1, m2 = movies[i], movies[j]
                users1, users2 = self.movie_ratings[m1], self.movie_ratings[m2]
                common_users = set(users1.keys()) & set(users2.keys())
                if len(common_users) < self.min_values:
                    sim = 0
                else:
                    num = sum((users1[u]-self.user_avg[u])*(users2[u]-self.user_avg[u]) for u in common_users)
                    den1 = sum((users1[u]-self.user_avg[u])**2 for u in common_users)
                    den2 = sum((users2[u]-self.user_avg[u])**2 for u in common_users)
                    if den1 > 0 and den2 > 0:
                        sim = num / math.sqrt(den1*den2)
                        if sim < self.threshold:
                            sim = 0
                    else:
                        sim = 0
                self.similarities[(m1,m2)] = sim
                self.similarities[(m2,m1)] = sim


    def similarity(self, p1, p2):
        return self.similarities.get((p1, p2), 0)

    def predict(self, user_id):
        predictions = {}
        user_ratings = self.X.user_ratings.get(user_id, {})
        
        for movie_i in self.filter:
            if movie_i in user_ratings:
                continue
            num, den = 0.0, 0.0
            for movie_j, rating_j in user_ratings.items():
                sim = self.similarity(movie_i, movie_j)
                if sim > 0:
                    num += sim * rating_j
                    den += abs(sim)
            if den > 0:
                predictions[movie_i] = num / den
        return predictions
    
    def similarItems(self, item, n):
        sims = []

        for (m1, m2), sim in self.similarities.items():
            if m1 == item and m2 != item and sim > 0:
                sims.append((m2, sim))

        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:n]



# Delete old pickle to avoid cached wrong data
import os
if os.path.exists("item_based_sim_min0_th0.pkl"):
    os.remove("item_based_sim_min0_th0.pkl")


md = MovieData('/home/stefanija/Desktop/os/hetrec2011-movielens-2k-v2(1)/movies.dat')
uim = UserItemData('/home/stefanija/Desktop/os/hetrec2011-movielens-2k-v2(1)/user_ratedmovies.dat')
rp = RandomPredictor(1, 5)
rec = Recommender(rp)
rec.fit(uim)
rec_items = rec.recommend(78, n=5, rec_seen=False)
for idmovie, val in rec_items:
    print("Film: {}, ocena: {}".format(md.get_title(idmovie), val))  

# Load users/movies
md = MovieData('/home/stefanija/Desktop/os/hetrec2011-movielens-2k-v2(1)/movies.dat')
uim = UserItemData('/home/stefanija/Desktop/os/hetrec2011-movielens-2k-v2(1)/user_ratedmovies.dat', min_ratings=1000)

# Predictor
rp = ItemBasedPredictor(min_values=1, threshold=0, use_pickle=False)  # 1 common user
rec = Recommender(rp)
rec.fit(uim)

pairs = []
for (m1, m2), sim in rp.similarities.items():
    if m1 != m2 and sim > 0:
        pairs.append((m1, m2, sim))

# sort by similarity descending
pairs.sort(key=lambda x: x[2], reverse=True)

# print top 20
for m1, m2, sim in pairs[:20]:
    print(
        f"Film1: {md.get_title(m1)}, "
        f"Film2: {md.get_title(m2)}, "
        f"podobnost: {sim}"
    )

print("BLABLABLAAAA")
rec_items = rp.similarItems(4993, 10)
print('Filmi podobni "The Lord of the Rings: The Fellowship of the Ring": ')
for idmovie, val in rec_items:
    print("Film: {}, ocena: {}".format(md.get_title(idmovie), val))




    



            
                    
    
    


                

            

            

        



        



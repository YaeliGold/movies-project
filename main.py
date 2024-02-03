from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import httpx
import random
import logging

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

TMDB_API_KEY = "96b6b5f3d9e0efafd624e3e9532ffaac"
TMDB_API_URL = "https://api.themoviedb.org/3"

logging.basicConfig(level=logging.DEBUG)

async def get_movie_genres():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TMDB_API_URL}/genre/movie/list",
                params={"api_key": TMDB_API_KEY}
            )
            response.raise_for_status()
            data = response.json()
            genres = data.get("genres", [])
            return [{"id": genre["id"], "name": genre["name"]} for genre in genres]
    except Exception as e:
        logging.error(f"An error occurred in get_movie_genres: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def get_movie_details(movie_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TMDB_API_URL}/movie/{movie_id}",
                params={"api_key": TMDB_API_KEY}
            )
            response.raise_for_status()
            data = response.json()
            return data
    except Exception as e:
        logging.error(f"An error occurred in get_movie_details: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

YEARS = list(range(2020, 2024))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        genres_list = await get_movie_genres()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "years": YEARS, "genres_list": genres_list},
            media_type="text/html",
            charset="utf-8"
        )
    except Exception as e:
        logging.error(f"An error occurred in read_root: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/recommend", response_class=HTMLResponse)
async def recommend_movie(
    request: Request,
    genre: int,
    year_preference: str,
    specific_year: Optional[int] = Query(None, alias="specific-year"),
    adult_can_watch: bool = False,
    adult_cannot_watch: bool = False,
):
    try:
        params = {"api_key": TMDB_API_KEY, "with_genres": str(genre)}

        if year_preference == "specific" and specific_year is not None:
            params["primary_release_year"] = specific_year

        # Check user preferences for adult movies
        if adult_can_watch and not adult_cannot_watch:
            params["include_adult"] = True
        elif adult_cannot_watch and not adult_can_watch:
            params["include_adult"] = False

        async with httpx.AsyncClient() as client:
            # Fetch movies based on user preferences
            response = await client.get(f"{TMDB_API_URL}/discover/movie", params=params)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            data = response.json()

            all_movies = data.get("results", [])
            print(f"Number of movies found: {len(all_movies)}")

            if not all_movies:
                print("No movies found.")

            for movie in all_movies:
                movie_id = movie.get("id")
                movie_data = await get_movie_details(movie_id)
                popularity_scaled = max(1, min(movie_data.get('popularity', 0) / 10, 100))
                movie['popularity'] = popularity_scaled

            selected_movies = random.sample(all_movies, min(5, len(all_movies)))
            print(f"Selected movies: {selected_movies}")

            return templates.TemplateResponse(
                "recommend.html",
                {"request": request, "year": specific_year, "selected_movies": selected_movies},
                media_type="text/html",
                charset="utf-8",
            )

    except httpx.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    except Exception as e:
        print(f"An error occurred in recommend_movie: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

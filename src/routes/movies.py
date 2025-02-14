from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database.models import ReactionModel, FavoriteModel, CommentModel
from database.models.films_features import ReactionEnum
from database.models.accounts import UserModel, UserGroupEnum
from database.models.movies import (
    MovieModel,
    CertificationModel,
    GenreModel,
    StarModel,
    DirectorModel,
    UserRatingModel
)
from database import get_db
from schemas.movies import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
    FavoriteSchema,
    CommentCreateSchema,
    CommentResponseSchema,
)
from services import get_current_user


router = APIRouter()


@router.get(
    "/movies/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of movies",
    description=(
        "<h3>This endpoint retrieves a paginated list of movies from the database. "
        "Clients can specify the `page` number and the number of items per page using `per_page`. "
        "The response includes details about the movies, total pages, and total items, "
        "along with links to the previous and next pages if applicable.</h3>"
    ),
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        }
    },
)
def get_movie_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    year: int | None = Query(None, description="Filter by release year"),
    min_imdb: float | None = Query(None, ge=0, le=10, description="Minimum IMDb rating"),
    max_imdb: float | None = Query(None, ge=0, le=10, description="Maximum IMDb rating"),
    director: str | None = Query(None, description="Filter by director name"),
    star: str | None = Query(None, description="Filter by actor name"),
    genre: str | None = Query(None, description="Filter by genre name"),
    search: str | None = Query(None, description="Search in movie name, description, director, or star"),
    sort_by: str | None = Query(None, description="Sort by 'price', 'year', 'votes'"),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
) -> MovieListResponseSchema:
    """
    Fetch a paginated list of movies from the database.

    This function retrieves a paginated list of movies, allowing the client to specify
    the page number and the number of items per page. It calculates the total pages
    and provides links to the previous and next pages when applicable.
    """
    query = db.query(MovieModel)

    if year:
        query = query.filter(MovieModel.year == year)
    if min_imdb:
        query = query.filter(MovieModel.imdb >= min_imdb)
    if max_imdb:
        query = query.filter(MovieModel.imdb <= max_imdb)
    if director:
        query = query.join(MovieModel.directors).filter(DirectorModel.name.ilike(f"%{director}%"))
    if star:
        query = query.join(MovieModel.stars).filter(StarModel.name.ilike(f"%{star}%"))
    if genre:
        query = query.join(MovieModel.genres).filter(GenreModel.name.ilike(f"%{genre}%"))

    if search:
        query = (
            query.outerjoin(MovieModel.directors)
            .outerjoin(MovieModel.stars)
            .filter(
                or_(
                    MovieModel.name.ilike(f"%{search}%"),
                    MovieModel.description.ilike(f"%{search}%"),
                    DirectorModel.name.ilike(f"%{search}%"),
                    StarModel.name.ilike(f"%{search}%"),
                )
            )
        )

    sort_fields = {
        "price": MovieModel.price,
        "year": MovieModel.year,
        "votes": MovieModel.votes,
    }
    if sort_by in sort_fields:
        query = query.order_by(sort_fields[sort_by].desc())

    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page

    movies = query.offset((page - 1) * per_page).limit(per_page).all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    response = MovieListResponseSchema(
        movies=[MovieListItemSchema.model_validate(movie) for movie in movies],
        prev_page=f"/cinema/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.get(
    "/movies/favorites/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of films in favorites",
    description="<h3>This endpoint allows clients to get list of favorite movies</h3>",
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        },
        401: {
            "description": "Token has expired.",
            "content": {"application/json": {"example": {"detail": "Token has expired."}}},
        },
    },
)
def favorite_movies(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    year: int | None = Query(None, description="Filter by release year"),
    min_imdb: float | None = Query(None, ge=0, le=10, description="Minimum IMDb rating"),
    max_imdb: float | None = Query(None, ge=0, le=10, description="Maximum IMDb rating"),
    director: str | None = Query(None, description="Filter by director name"),
    star: str | None = Query(None, description="Filter by actor name"),
    genre: str | None = Query(None, description="Filter by genre name"),
    search: str | None = Query(None, description="Search in movie name, description, director, or star"),
    sort_by: str | None = Query(None, description="Sort by 'price', 'year', 'votes'"),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
) -> MovieListResponseSchema:
    """
    Fetch a paginated list of favorite movies from the database.

    This function retrieves a paginated list of favorite movies, allowing the client to specify
    the page number and the number of items per page. It calculates the total pages
    and provides links to the previous and next pages when applicable.
    """
    query = (
        db.query(MovieModel)
        .join(FavoriteModel, FavoriteModel.movie_id == MovieModel.id)
        .filter(FavoriteModel.favorite == True, FavoriteModel.user_id == user.id)
    )

    if year:
        query = query.filter(MovieModel.year == year)
    if min_imdb:
        query = query.filter(MovieModel.imdb >= min_imdb)
    if max_imdb:
        query = query.filter(MovieModel.imdb <= max_imdb)
    if director:
        query = query.join(MovieModel.directors).filter(DirectorModel.name.ilike(f"%{director}%"))
    if star:
        query = query.join(MovieModel.stars).filter(StarModel.name.ilike(f"%{star}%"))
    if genre:
        query = query.join(MovieModel.genres).filter(GenreModel.name.ilike(f"%{genre}%"))

    if search:
        query = (
            query.outerjoin(MovieModel.directors)
            .outerjoin(MovieModel.stars)
            .filter(
                or_(
                    MovieModel.name.ilike(f"%{search}%"),
                    MovieModel.description.ilike(f"%{search}%"),
                    DirectorModel.name.ilike(f"%{search}%"),
                    StarModel.name.ilike(f"%{search}%"),
                )
            )
        )

    sort_fields = {
        "price": MovieModel.price,
        "year": MovieModel.year,
        "votes": MovieModel.votes,
    }
    if sort_by in sort_fields:
        query = query.order_by(sort_fields[sort_by].desc())

    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page

    movies = query.offset((page - 1) * per_page).limit(per_page).all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    response = MovieListResponseSchema(
        movies=[MovieListItemSchema.model_validate(movie) for movie in movies],
        prev_page=f"/cinema/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/cinema/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.post(
    "/movies/",
    response_model=MovieDetailSchema,
    summary="Add a new movie",
    description=(
        "<h3>This endpoint allows clients to add a new movie to the database. "
        "It accepts details such as name, date, genres, stars, directors, and "
        "other attributes. The associated certification, genres, stars, and directors "
        "will be created or linked automatically.</h3>"
    ),
    responses={
        201: {
            "description": "Movie created successfully.",
        },
        400: {
            "description": "Invalid input.",
            "content": {"application/json": {"example": {"detail": "Invalid input data."}}},
        },
    },
    status_code=201,
)
def create_movie(
        movie_data: MovieCreateSchema,
        db: Session = Depends(get_db),
        user: UserModel = Depends(get_current_user)
) -> MovieDetailSchema:
    """
    Add a new movie to the database.

    This endpoint allows the creation of a new movie with details such as
    name, release date, genres, stars, and directors. It automatically
    handles linking or creating related entities.
    """
    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=403, detail="You are not have access to perform this action."
        )

    existing_movie = (
        db.query(MovieModel).filter(MovieModel.name == movie_data.name, MovieModel.year == movie_data.year).first()
    )

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie_data.name}' and release year '{movie_data.year}' already exists.",
        )

    try:
        certification = db.query(CertificationModel).filter_by(name=movie_data.certification).first()
        if not certification:
            certification = CertificationModel(name=movie_data.certification)
            db.add(certification)
            db.flush()

        genres = []
        for genre_name in movie_data.genres:
            genre = db.query(GenreModel).filter_by(name=genre_name).first()
            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                db.flush()
            genres.append(genre)

        stars = []
        for star_name in movie_data.stars:
            star = db.query(StarModel).filter_by(name=star_name).first()
            if not star:
                star = StarModel(name=star_name)
                db.add(star)
                db.flush()
            stars.append(star)

        directors = []
        for director_name in movie_data.directors:
            director = db.query(DirectorModel).filter_by(name=director_name).first()
            if not director:
                director = DirectorModel(name=director_name)
                db.add(director)
                db.flush()
            directors.append(director)

        movie = MovieModel(
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            genres=genres,
            stars=stars,
            directors=directors,
            certification=certification,
        )
        db.add(movie)
        db.commit()
        db.refresh(movie)

        return MovieDetailSchema.model_validate(movie)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data.")


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Get movie details by ID",
    description=(
        "<h3>Fetch detailed information about a specific movie by its unique ID. "
        "This endpoint retrieves all available details for the movie, such as "
        "its name, genre, crew, budget, and revenue. If the movie with the given "
        "ID is not found, a 404 error will be returned.</h3>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {"application/json": {"example": {"detail": "Movie with the given ID was not found."}}},
        }
    },
)
def get_movie_by_id(
    movie_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
) -> MovieDetailSchema:
    """
    Retrieve detailed information about a specific movie by its ID.

    This function fetches detailed information about a movie identified by its unique ID.
    If the movie does not exist, a 404 error is returned.
    """
    movie = (
        db.query(MovieModel)
        .options(
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors),
            joinedload(MovieModel.certification),
        )
        .filter(MovieModel.id == movie_id)
        .first()
    )

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return MovieDetailSchema.model_validate(movie)


@router.delete(
    "/movies/{movie_id}/",
    summary="Delete a movie by ID",
    description=(
        "<h3>Delete a specific movie from the database by its unique ID.</h3>"
        "<p>If the movie exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
    ),
    responses={
        204: {"description": "Movie deleted successfully."},
        404: {
            "description": "Movie not found.",
            "content": {"application/json": {"example": {"detail": "Movie with the given ID was not found."}}},
        },
    },
    status_code=204,
)
def delete_movie(
    movie_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    """
    Delete a specific movie by its ID.

    This function deletes a movie identified by its unique ID.
    If the movie does not exist, a 404 error is raised.
    """
    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=403, detail="You are not have access to perform this action."
        )

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    db.delete(movie)
    db.commit()
    return {"detail": "Movie deleted successfully."}


@router.patch(
    "/movies/{movie_id}/",
    summary="Update a movie by ID",
    description=(
        "<h3>Update details of a specific movie by its unique ID.</h3>"
        "<p>This endpoint updates the details of an existing movie. If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Movie updated successfully.",
            "content": {"application/json": {"example": {"detail": "Movie updated successfully."}}},
        },
        404: {
            "description": "Movie not found.",
            "content": {"application/json": {"example": {"detail": "Movie with the given ID was not found."}}},
        },
    },
)
def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user)
):
    """
    Update a specific movie by its ID.

    This function updates a movie identified by its unique ID.
    If the movie does not exist, a 404 error is raised.
    """
    if user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=403, detail="You are not have access to perform this action."
        )

    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)

    try:
        db.commit()
        db.refresh(movie)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
    else:
        return {"detail": "Movie updated successfully."}


@router.get(
    "/genres/",
    summary="Get list of genres",
    description=("<h3>This endpoint retrieves a list of genres with the count of movies in each.</h3>"),
    responses={
        404: {
            "description": "No genres found.",
            "content": {"application/json": {"example": {"detail": "No genres found."}}},
        }
    },
)
def get_genres(db: Session = Depends(get_db), user: UserModel = Depends(get_current_user)):
    genres_with_movie_count = (
        db.query(GenreModel, func.count(MovieModel.id).label("movie_count"))
        .join(MovieModel.genres)
        .group_by(GenreModel.id)
        .all()
    )

    result = [{"name": genre.name, "movie_count": movie_count} for genre, movie_count in genres_with_movie_count]

    return result


@router.get(
    "/genres/{genre_name}/",
    summary="Get genre details by genre name.",
    description=("<h3>This endpoint retrieves a genre with all related movies.</h3>"),
    responses={
        404: {
            "description": "No genres found.",
            "content": {"application/json": {"example": {"detail": "No genres found."}}},
        }
    },
)
def get_movies_by_genre(
        genre_name: str,
        db: Session = Depends(get_db),
        user: UserModel = Depends(get_current_user)
):
    genre = db.query(GenreModel).filter(GenreModel.name.ilike(genre_name)).first()
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre.movies


@router.put(
    "/movies/{movie_id}/rate",
    summary="Rate a movie by its ID",
    description=("<h3>Rate movies on a 10-point scale.</h3>"),
    responses={
        400: {
            "description": "Bad Request - The provided refresh token is invalid or expired.",
            "content": {"application/json": {"example": {"detail": "Token has expired."}}},
        },
        401: {
            "description": "Unauthorized - Refresh token not found.",
            "content": {"application/json": {"example": {"detail": "Refresh token not found."}}},
        },
        404: {
            "description": "Not Found - The movie does not exist.",
            "content": {"application/json": {"example": {"detail": "Movie not found."}}},
        },
    },
)
def rate_movie(
        movie_id: int,
        rating: int = Query(ge=0, le=10),
        db: Session = Depends(get_db),
        user: UserModel = Depends(get_current_user),
):
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    user_rating = db.query(UserRatingModel).filter_by(user_id=user.id, movie_id=movie.id).first()

    if user_rating:
        previous_rating = user_rating.rating
        user_rating.rating = rating
    else:
        previous_rating = None
        user_rating = UserRatingModel(user_id=user.id, movie_id=movie.id, rating=rating)
        db.add(user_rating)
        movie.votes += 1

    if previous_rating is not None:
        total_rating = (movie.rating * movie.votes) - previous_rating + rating
    else:
        total_rating = (movie.rating * (movie.votes - 1)) + rating

    movie.rating = round(total_rating / movie.votes, 1)

    db.commit()

    return MovieDetailSchema.model_validate(movie)


@router.get(
    "/movies/{movie_id}/like/",
    response_model=MovieDetailSchema,
    summary="Add like to movie",
    description="<h3>This endpoint allows clients to like movie</h3>",
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        },
        401: {
            "description": "Token has expired.",
            "content": {"application/json": {"example": {"detail": "Token has expired."}}},
        },
    },
)
def like_movie(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:
        raise HTTPException(status_code=404, detail="No movies found.")


    like = db.query(ReactionModel).filter(ReactionModel.movie_id == movie_id, ReactionModel.user_id == user.id).first()

    if not like:
        like = ReactionModel(movie_id=movie_id, user_id=user.id, reaction=ReactionEnum.LIKE)
        db.add(like)
        movie.likes += 1
    elif like.reaction == ReactionEnum.LIKE:
        db.delete(like)
        movie.likes -= 1
        db.commit()
        db.refresh(movie)
        return MovieDetailSchema.model_validate(movie)
    else:
        like.reaction = ReactionEnum.LIKE
        movie.dislikes -= 1
        movie.likes += 1

    db.commit()
    db.refresh(movie)
    db.refresh(like)

    return MovieDetailSchema.model_validate(movie)


@router.get(
    "/movies/{movie_id}/dislike/",
    response_model=MovieDetailSchema,
    summary="Add dislike to movie",
    description="<h3>This endpoint allows clients to dislike movie</h3>",
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        },
        401: {
            "description": "Token has expired.",
            "content": {"application/json": {"example": {"detail": "Token has expired."}}},
        },
    },
)
def dislike_movie(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:
        raise HTTPException(status_code=404, detail="No movies found.")

    dislike = (
        db.query(ReactionModel).filter(ReactionModel.movie_id == movie_id, ReactionModel.user_id == user.id).first()
    )

    if not dislike:
        dislike = ReactionModel(movie_id=movie_id, user_id=user.id, reaction=ReactionEnum.DISLIKE)
        db.add(dislike)
        movie.dislikes += 1
    elif dislike.reaction == ReactionEnum.DISLIKE:
        db.delete(dislike)
        movie.dislikes -= 1
        db.commit()
        db.refresh(movie)
        return MovieDetailSchema.model_validate(movie)
    else:
        dislike.reaction = ReactionEnum.DISLIKE
        movie.likes -= 1
        movie.dislikes += 1

    db.commit()
    db.refresh(dislike)
    db.refresh(movie)

    return MovieDetailSchema.model_validate(movie)


@router.post(
    "/movies/{movie_id}/comment/",
    response_model=CommentResponseSchema,
    summary="Add comment to movie",
    description="<h3>This endpoint allows clients to comment movie</h3>",
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        },
        401: {
            "description": "Token has expired.",
            "content": {"application/json": {"example": {"detail": "Token has expired."}}},
        },
    },
)
def comment_movie(
    movie_id: int,
    comment_data: CommentCreateSchema,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="No movies found.")


    comment = CommentModel(movie_id=movie_id, user_id=user.id, comment=comment_data.comment)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return CommentResponseSchema.model_validate(comment)


@router.post(
    "/movies/{movie_id}/{parent_id}/comment/",
    response_model=CommentResponseSchema,
    summary="Add comment to comment",
    description="<h3>This endpoint allows clients to comment comment</h3>",
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        },
        401: {
            "description": "Token has expired.",
            "content": {"application/json": {"example": {"detail": "Token has expired."}}},
        },
    },
)
def comment_movie_comment(
    movie_id: int,
    parent_id: int,
    comment_data: CommentCreateSchema,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="No movies found.")

    parent_comment = None
    if parent_id != 0:
        parent_comment = db.query(CommentModel).filter(CommentModel.id == parent_id).first()
        if not parent_comment:
            raise HTTPException(status_code=404, detail="No comments found.")

    comment = CommentModel(
        movie_id=movie_id,
        user_id=user.id,
        parent_id=parent_comment.id if parent_comment else None,
        comment=comment_data.comment,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return CommentResponseSchema.model_validate(comment)


@router.get(
    "/movies/{movie_id}/favorite/",
    response_model=FavoriteSchema,
    summary="Add movie to favorite",
    description="<h3>This endpoint allows clients to add movie to favorite</h3>",
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        },
        401: {
            "description": "Token has expired.",
            "content": {"application/json": {"example": {"detail": "Token has expired."}}},
        },
    },
)
def favorite_movie(
    movie_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:
        raise HTTPException(status_code=404, detail="No movies found.")

    favorite = (
        db.query(FavoriteModel).filter(FavoriteModel.movie_id == movie_id, FavoriteModel.user_id == user.id).first()
    )
    if not favorite:
        favorite = FavoriteModel(movie_id=movie_id, user_id=user.id, favorite=True)
        db.add(favorite)
    else:
        favorite.favorite = not favorite.favorite

    db.commit()
    db.refresh(favorite)

    return FavoriteSchema.model_validate(favorite)

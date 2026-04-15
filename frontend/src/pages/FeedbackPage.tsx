import { FormEvent, useCallback, useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { deleteFeedback, getFeedback, saveFeedback } from "../api";
import { useAppState } from "../state";

const RATING_TEXTS = [
  "",
  "Плохо/Poor",
  "Удовлетворительно/Fair",
  "Нормально/Good",
  "Хорошо/Very Good",
  "Отлично/Excellent"
];

export function FeedbackPage() {
  const navigate = useNavigate();
  const { userLogin, isDark, setThemeDark } = useAppState();
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [feedbackText, setFeedbackText] = useState("");
  const [hasExisting, setHasExisting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState({ message: "", show: false });

  const showNotification = useCallback((message: string) => {
    setNotification({ message, show: true });
    window.setTimeout(() => setNotification((n) => ({ ...n, show: false })), 3000);
  }, []);

  const loadExisting = useCallback(async () => {
    try {
      const { feedback } = await getFeedback();
      if (feedback) {
        setRating(feedback.rating);
        setFeedbackText(feedback.feedback_text);
        setHasExisting(true);
      } else {
        setHasExisting(false);
      }
    } catch {
      setHasExisting(false);
    }
  }, [userLogin]);

  useEffect(() => {
    if (userLogin) {
      void loadExisting();
    }
  }, [userLogin, loadExisting]);

  const displayRating = hoverRating || rating;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (rating < 1) {
      showNotification("Пожалуйста, выберите оценку/Please select a rating");
      return;
    }
    if (!feedbackText.trim()) {
      showNotification("Пожалуйста, заполните все поля/Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      await saveFeedback(rating, feedbackText.trim());
      showNotification("Thank you for your feedback!");
      setHasExisting(true);
    } catch {
      showNotification(
        "Не удалось отправить отзыв. Пожалуйста, попробуйте снова или свяжитесь с администратором."
      );
    } finally {
      setLoading(false);
    }
  }

  async function onDelete() {
    if (!window.confirm("Вы уверены, что хотите удалить ваш отзыв?/Are you sure you want to delete your feedback?")) {
      return;
    }
    setLoading(true);
    try {
      await deleteFeedback();
      setRating(0);
      setFeedbackText("");
      setHasExisting(false);
      showNotification("Feedback deleted successfully!");
    } catch {
      showNotification("Не удалось удалить отзыв.");
    } finally {
      setLoading(false);
    }
  }

  if (!userLogin) {
    return <Navigate to="/" replace />;
  }

  return (
    <>
      <div className="container">
        <div className="app-header">
          <div className="language-theme">
            <label className="theme-switch" htmlFor="themeToggle">
              <input
                id="themeToggle"
                type="checkbox"
                checked={isDark}
                onChange={(e) => setThemeDark(e.target.checked)}
              />
              <span className="theme-slider">
                <span className="theme-thumb">
                  <span className="theme-thumb-icon sun">{"\u2600\uFE0F"}</span>
                  <span className="theme-thumb-icon moon">{"\uD83C\uDF19"}</span>
                </span>
              </span>
            </label>
          </div>
          <div className="navigation-arrows">
            <img
              src={isDark ? "/src/emblem_dark.png" : "/src/emblem.png"}
              alt="Emblem"
              className="emblem-img"
            />
          </div>
          <div />
        </div>

        <div className="feedback-container">
          <h1 className="feedback-title">Обратная связь/Feedback</h1>
          <p className="feedback-subtitle">
            Поделитесь своим мнением о нашем сервисе/Share your opinion about our service
          </p>

          <form id="feedbackForm" onSubmit={(e) => void onSubmit(e)}>
            <div className="rating-section">
              <label className="rating-label">Оцените наш сервис/Rate our service</label>
              <div
                className="stars-container"
                onMouseLeave={() => setHoverRating(0)}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <span
                    key={n}
                    className={`star ${n <= displayRating ? "active selected" : ""}`}
                    data-rating={n}
                    role="button"
                    tabIndex={0}
                    onClick={() => setRating(n)}
                    onMouseEnter={() => setHoverRating(n)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setRating(n);
                      }
                    }}
                  >
                    <img
                      src={n <= displayRating ? "/src/star_nonempty.png" : "/src/star_empty.png"}
                      alt="star"
                    />
                  </span>
                ))}
              </div>
              <div className="rating-text" id="ratingText">
                {displayRating > 0 ? RATING_TEXTS[displayRating] : ""}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="feedbackText">
                Ваш отзыв/Your feedback
              </label>
              <textarea
                id="feedbackText"
                name="feedbackText"
                className="form-textarea"
                placeholder="Напишите ваш отзыв здесь.../Write your feedback here..."
                required
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
              />
            </div>

            <button type="submit" className="submit-button">
              Отправить/Submit
            </button>
            {hasExisting ? (
              <button type="button" className="delete-button" id="deleteButton" onClick={() => void onDelete()}>
                Удалить отзыв/Delete Feedback
              </button>
            ) : null}
            <button type="button" className="back-button" id="backButton" onClick={() => navigate("/menu")}>
              Вернуться к меню/Back to Menu
            </button>
          </form>
        </div>
      </div>

      <div className={`notification${notification.show ? " show" : ""}`}>{notification.message}</div>

      <div className={`loading-overlay ${loading ? "" : "hidden"}`} id="loadingOverlay">
        <div className="loading-content">
          <div className="loading-spinner" />
          <div className="loading-text" id="loadingText">
            Sending...
          </div>
        </div>
      </div>
    </>
  );
}

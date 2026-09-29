import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button, Card, EmptyState, LoadingScreen, PageHeader, ProgressBar, ProgressRing } from "../components/ui";

export default function MyLearning() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/my/learning").then((res) => {
      setCourses(res.data);
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingScreen label="Loading your courses…" />;

  const inProgress = courses.filter((c) => c.progress_pct > 0 && c.progress_pct < 1);
  const notStarted = courses.filter((c) => c.progress_pct === 0);
  const finished = courses.filter((c) => c.progress_pct === 1);

  return (
    <div>
      <PageHeader eyebrow="Dashboard" title="My learning" description="Pick up where you left off." />

      {courses.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon="🎓"
            title="You haven't enrolled in any courses yet"
            description="Head to the Course Catalog to get started."
            action={<Button onClick={() => navigate("/catalog")}>Browse catalog</Button>}
          />
        </div>
      ) : (
        <div className="mt-6 space-y-8">
          {inProgress.length > 0 && (
            <Section title="Continue learning" courses={inProgress} navigate={navigate} />
          )}
          {notStarted.length > 0 && <Section title="Not started" courses={notStarted} navigate={navigate} />}
          {finished.length > 0 && <Section title="Completed" courses={finished} navigate={navigate} />}
        </div>
      )}
    </div>
  );
}

function Section({ title, courses, navigate }) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-500">{title}</h2>
      <div className="mt-3 space-y-3">
        {courses.map((c) => (
          <Card key={c.id} className="flex items-center gap-4">
            <ProgressRing value={c.progress_pct} />
            <div className="min-w-0 flex-1">
              <h3 className="truncate font-display text-base font-semibold text-ink-900">{c.title}</h3>
              <ProgressBar value={c.progress_pct} className="mt-2 max-w-md" />
              <div className="mt-1 text-xs text-ink-500">
                {c.lessons_completed}/{c.lessons_total} completed
              </div>
            </div>
            <Button className="flex-shrink-0" onClick={() => navigate(`/course/${c.id}`)}>
              {c.progress_pct === 0 ? "Start course" : c.progress_pct === 1 ? "Review" : "Continue"} ▶
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}

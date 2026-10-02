import { useMemo, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api, staticUrl } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Badge, Button, Card, EmptyState, Input, LoadingScreen, PageHeader, RichText } from "../components/ui";

export default function Catalog() {
  const { user } = useAuth();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");

  async function load() {
    setLoading(true);
    const res = await api.get("/courses");
    setCourses(res.data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function handlePreviewEnroll(courseId) {
    await api.post(`/enrollments/preview/${courseId}`);
    load();
  }

  const categories = useMemo(() => {
    const set = new Set(courses.map((c) => c.category).filter(Boolean));
    return ["All", ...set];
  }, [courses]);

  const filtered = courses.filter((c) => {
    const matchesCategory = category === "All" || c.category === category;
    const matchesQuery =
      !query ||
      c.title.toLowerCase().includes(query.toLowerCase()) ||
      c.description?.toLowerCase().includes(query.toLowerCase());
    return matchesCategory && matchesQuery;
  });

  if (loading) return <LoadingScreen label="Loading catalog…" />;

  return (
    <div>
      <PageHeader
        eyebrow="Catalog"
        title="Course catalog"
        description="Practical, hands-on courses in AI, ML, cybersecurity, and emerging technologies."
      />

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search courses…"
          className="sm:max-w-xs"
        />
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                category === cat ? "bg-brand-600 text-white" : "bg-white text-ink-600 border border-ink-200 hover:bg-ink-50"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 && (
        <div className="mt-8">
          <EmptyState
            icon="🔍"
            title={courses.length === 0 ? "No courses published yet" : "No courses match your search"}
            description={courses.length === 0 ? "Check back soon." : "Try a different keyword or category."}
          />
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {filtered.map((c) => (
          <Card key={c.id} padded={false} className="flex flex-col overflow-hidden transition hover:shadow-card-lg">
            <div className="aspect-video w-full overflow-hidden bg-ink-100">
              {c.thumbnail_url ? (
                <img
                  src={
                    c.thumbnail_url.startsWith("http") || c.thumbnail_url.startsWith("data:")
                      ? c.thumbnail_url
                      : staticUrl(c.thumbnail_url)
                  }
                  alt={c.title}
                  className="h-full w-full object-cover"
                  onError={(e) => (e.currentTarget.style.display = "none")}
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-4xl">📘</div>
              )}
            </div>
            <div className="flex flex-1 flex-col p-5">
              <div className="flex items-center gap-2">
                {c.category && <Badge variant="brand">{c.category}</Badge>}
                {c.is_free && <Badge variant="success">Free</Badge>}
              </div>
              <h2 className="mt-2.5 font-display text-base font-bold text-ink-900">{c.title}</h2>
              <RichText text={c.description} className="mt-1.5 line-clamp-3 flex-1 text-sm text-ink-500" />

              <div className="mt-4">
                {c.is_enrolled ? (
                  <Button as={Link} to={`/course/${c.id}`} variant="success" className="w-full">
                    ▶ Continue learning
                  </Button>
                ) : user.role === "admin" ? (
                  <Button variant="secondary" className="w-full" onClick={() => handlePreviewEnroll(c.id)}>
                    Enroll (preview)
                  </Button>
                ) : (
                  <div className="rounded-lg bg-warning-50 px-3 py-2 text-xs font-medium text-warning-700">
                    {user.role === "instructor"
                      ? "🔒 Not assigned to you — only courses assigned to you are accessible."
                      : "🔒 Not enrolled — contact D'siar Tech to purchase access."}
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
